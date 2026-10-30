import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Следующее действие миграции по карте (скилл orchestrator). Запуск из корня проекта:
 *
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/NextAction.java              - что делать дальше
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/NextAction.java M-012        - можно ли взять этот юнит
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/NextAction.java M-001..M-005 - пачка (или список через запятую)
 *
 * Печатает строку «ДЕЙСТВИЕ: ...» и строку «ПОЧЕМУ: ...». Карту не меняет. Единственное, что
 * пишет, - агенты кита: копирует <каталог скилла>/agents/*.md в .gigacode/agents/ проекта,
 * если их там нет или они отличаются.
 */
public class NextAction {

    private static final Path MIGRATION = Paths.get(".gigacode", "data", "migration");
    private static final Path AGENTS = Paths.get(".gigacode", "agents");
    private static final int BATCH_LIMIT = 5;
    private static final List<String> STATUSES = List.of("todo", "in-progress", "done", "blocked");
    private static final List<String> BROKEN_ROWS = new ArrayList<>();

    public static void main(String[] args) throws IOException {
        System.setOut(new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8));
        List<String> installed = installAgents();
        if (!installed.isEmpty()) {
            say("агенты установлены", "в .gigacode/agents/ записаны: " + String.join(", ", installed)
                    + " - GigaCode читает агентов при запуске: перезапустите GigaCode (выйдите и запустите заново) и повторите запрос");
            return;
        }
        Path mapFile = MIGRATION.resolve("MIGRATION-MAP.md");
        if (!Files.exists(mapFile)) {
            say("migration-map", "карты нет - строим с Этапа 1");
            return;
        }
        String text = Files.readString(mapFile, StandardCharsets.UTF_8);
        Map<String, String> head = frontMatter(text);
        String status = head.getOrDefault("map_status", "-");
        List<String> markup = markupQuestions(text);
        if (!markup.isEmpty()) {
            say("вопросы разметки", "ждём ответов человека: " + String.join(", ", markup)
                    + " - запусти migration-map: он выведет блок вопросов (Этап 2, шаг 1б) и остановится;"
                    + " ответы приходят сообщением с JSON {\"answers\": {\"Q-<n>\": \"<значение>\"}}");
            return;
        }
        if (status.equals("building")) {
            say("migration-map", "карта строится, продолжить с этапа " + head.getOrDefault("map_stage", "?")
                    + openQuestionsNote(text));
            return;
        }
        if (status.equals("review")) {
            say("одобрение карты", "карта построена, но не утверждена: запусти migration-map - самопроверка Этапа 6 и утверждение без человека");
            return;
        }
        List<String> open = openQuestions(text);
        if (!open.isEmpty()) {
            say("вопросы", "в разделе 6 без ответа: " + String.join(", ", open) + " - доведи их до решения без человека (references/questions.md), потом снова NextAction");
            return;
        }
        List<Unit> units = units(text);
        Set<String> archived = archived(text);
        boolean core = head.getOrDefault("scope", "full").equals("core");
        if (!BROKEN_ROWS.isEmpty()) {
            say("карта повреждена", "в разделе 4 строки юнитов не разбираются (нужно 8 колонок и статус "
                    + String.join("/", STATUSES) + "): " + String.join(" | ", BROKEN_ROWS)
                    + " - исправь таблицу, юниты не запускаются");
            return;
        }
        if (units.isEmpty() && archived.isEmpty()) {
            say("карта повреждена", "в разделе 4 нет ни одного юнита и строки «В архиве» - исправь таблицу, юниты не запускаются");
            return;
        }

        if (args.length > 0) {
            requested(args[0], units, archived, core);
            mapSizeNote(text);
            return;
        }

        for (Unit unit : units) {
            if (unit.status.equals("in-progress") && allowed(unit, core)) {
                say("migration-step " + unit.id, "юнит in-progress - продолжить с места остановки" + nextStep(unit));
                mapSizeNote(text);
                return;
            }
        }
        for (Unit unit : units) {
            if (unit.status.equals("todo") && allowed(unit, core) && depsDone(unit, units, archived, core)) {
                say("migration-step " + unit.id, "первый todo сверху, все зависимости done" + nextStep(unit));
                mapSizeNote(text);
                return;
            }
        }
        boolean allDone = units.stream().allMatch(u -> u.status.equals("done"));
        if (core && units.stream().filter(u -> !u.status.equals("done")).allMatch(u -> !allowed(u, true))) {
            say("ядро готово", "scope: core - ядро переведено, тесты не тронуты; дальше - только по просьбе о полной миграции");
            return;
        }
        if (!allDone) {
            List<String> blocked = new ArrayList<>();
            for (Unit unit : units) {
                if (unit.status.equals("blocked")) {
                    blocked.add(unit.id);
                }
            }
            say("заблокировано", "доступных юнитов нет; blocked: " + (blocked.isEmpty() ? "-" : String.join(", ", blocked))
                    + "; остальные todo ждут их. Покажи блокеры из карточек и строки «решить человеку»");
            return;
        }
        String review = head.getOrDefault("review_status", "-");
        int round = parseInt(head.getOrDefault("review_round", "0"));
        if (review.equals("clean")) {
            say("финал", "все юниты done, проверка миграции чистая (круг " + round + ")");
        } else if (review.equals("findings") && round >= 3) {
            say("проверка не сходится", "три круга проверки с находками - покажи сводку последнего круга, дальше решает человек");
        } else {
            say("migration-review", "все юниты done, проверка миграции " + (round == 0 ? "ещё не запускалась" : "круг " + (round + 1)));
        }
        mapSizeNote(text);
    }

    /** Пользователь назвал юнит, диапазон или список. */
    private static void requested(String request, List<Unit> units, Set<String> archived, boolean core) {
        List<String> ids = new ArrayList<>();
        Matcher range = Pattern.compile("(M-[0-9]+)\\s*\\.\\.\\s*(M-[0-9]+)").matcher(request);
        if (range.find()) {
            boolean in = false;
            for (Unit unit : units) {
                if (unit.id.equals(range.group(1))) {
                    in = true;
                }
                if (in) {
                    ids.add(unit.id);
                }
                if (unit.id.equals(range.group(2))) {
                    break;
                }
            }
        } else {
            Matcher id = Pattern.compile("M-[0-9]+").matcher(request);
            while (id.find()) {
                ids.add(id.group());
            }
        }
        List<String> notes = new ArrayList<>();
        List<String> batch = new ArrayList<>();
        Set<String> earlier = new LinkedHashSet<>();
        for (String id : ids) {
            Unit unit = find(units, id);
            if (unit == null) {
                notes.add(id + " нет в таблице" + (archived.contains(id) ? " (в архиве - done)" : ""));
                continue;
            }
            if (unit.status.equals("done")) {
                notes.add(id + " уже done - пропущен");
                continue;
            }
            if (!allowed(unit, core)) {
                notes.add(id + " недоступен при scope: core");
                continue;
            }
            if (batch.size() == BATCH_LIMIT) {
                notes.add(id + " - следующей пачкой (больше " + BATCH_LIMIT + ")");
                continue;
            }
            for (String dep : unit.deps) {
                Unit depUnit = find(units, dep);
                boolean ok = earlier.contains(dep) || depSatisfied(dep, units, archived, core);
                if (!ok) {
                    say("нельзя", id + " ждёт " + dep + " (" + (depUnit == null ? "нет в таблице" : depUnit.status) + ")"
                            + (notes.isEmpty() ? "" : "; " + String.join("; ", notes)));
                    return;
                }
            }
            batch.add(id);
            earlier.add(id);
        }
        if (batch.isEmpty()) {
            say("нечего делать", notes.isEmpty() ? "юниты не найдены" : String.join("; ", notes));
        } else if (batch.size() == 1) {
            say("migration-step " + batch.get(0), "назван пользователем" + (notes.isEmpty() ? "" : "; " + String.join("; ", notes)));
        } else {
            say("migration-step пачка: " + String.join(", ", batch), "пачка проверена" + (notes.isEmpty() ? "" : "; " + String.join("; ", notes)));
        }
    }

    // ---------- разбор карты ----------

    static final class Unit {
        String id;
        String type;
        String status;
        List<String> deps = new ArrayList<>();
    }

    private static List<Unit> units(String text) {
        List<Unit> units = new ArrayList<>();
        for (String line : section(text, "4.").split("\n")) {
            String[] cells = cells(line);
            if (line.trim().startsWith("| M-") && (cells.length < 8 || !cells[0].matches("M-[0-9]+")
                    || !STATUSES.contains(cells[cells.length - 1]))) {
                BROKEN_ROWS.add(line.trim());
                continue;
            }
            if (cells.length >= 8 && cells[0].matches("M-[0-9]+")) {
                Unit unit = new Unit();
                unit.id = cells[0];
                unit.type = cells[2];
                unit.status = cells[7];
                Matcher dep = Pattern.compile("M-[0-9]+").matcher(cells[5]);
                while (dep.find()) {
                    unit.deps.add(dep.group());
                }
                units.add(unit);
            }
        }
        return units;
    }

    private static Set<String> archived(String text) {
        Set<String> ids = new LinkedHashSet<>();
        Matcher line = Pattern.compile("(?m)^В архиве[^:]*:(.*)$").matcher(text);
        if (!line.find()) {
            return ids;
        }
        Matcher part = Pattern.compile("M-([0-9]+)(?:\\s*\\.\\.\\s*M-([0-9]+))?").matcher(line.group(1));
        while (part.find()) {
            int from = Integer.parseInt(part.group(1));
            int to = part.group(2) == null ? from : Integer.parseInt(part.group(2));
            int width = part.group(1).length();
            for (int i = from; i <= to; i++) {
                ids.add("M-" + String.format("%0" + width + "d", i));
            }
        }
        return ids;
    }

    /** Записи раздела 6 с «ответ: -», кроме вопросов разметки: их решает только человек. */
    private static List<String> openQuestions(String text) {
        List<String> open = questions(text, false);
        open.removeAll(markupQuestions(text));
        return open;
    }

    /** Вопросы разметки без ответа («относится к: разметка:<ключ>») - единственные вопросы человеку. */
    private static List<String> markupQuestions(String text) {
        return questions(text, true);
    }

    private static List<String> questions(String text, boolean markupOnly) {
        List<String> open = new ArrayList<>();
        String current = null;
        boolean markup = false;
        for (String line : section(text, "6.").split("\n")) {
            Matcher q = Pattern.compile("^- (Q-[0-9]+)").matcher(line.trim().isEmpty() ? "" : line);
            if (q.find()) {
                current = q.group(1);
                markup = line.contains("относится к: разметка:");
            } else if (current != null && line.trim().matches("- ответ:\\s*-\\s*") && (markup || !markupOnly)) {
                open.add(current);
            }
        }
        return open;
    }

    private static String openQuestionsNote(String text) {
        List<String> open = openQuestions(text);
        return open.isEmpty() ? "" : "; вопросы без ответа: " + String.join(", ", open)
                + " - доведи их до решения без человека (orchestrator, references/questions.md)";
    }

    private static boolean allowed(Unit unit, boolean core) {
        if (!core) {
            return true;
        }
        if (unit.type.equals("env")) {
            return true;
        }
        return unit.type.equals("tech") && coreStepsLeft(unit.id) > 0;
    }

    /** Несделанные подшаги разбор/env/core в карточке tech. */
    private static int coreStepsLeft(String id) {
        try {
            String card = Files.readString(MIGRATION.resolve("units").resolve(id + ".md"), StandardCharsets.UTF_8);
            int left = 0;
            for (String line : card.split("\n")) {
                String[] cells = cells(line);
                if (cells.length >= 5 && cells[0].matches("S-[0-9]+") && cells[1].matches("разбор|env|core")
                        && !cells[4].equals("done")) {
                    left++;
                }
            }
            return left;
        } catch (IOException e) {
            return 0;
        }
    }

    private static String nextStep(Unit unit) {
        if (!unit.type.equals("tech")) {
            return "";
        }
        try {
            String card = Files.readString(MIGRATION.resolve("units").resolve(unit.id + ".md"), StandardCharsets.UTF_8);
            int done = 0;
            int total = 0;
            String next = null;
            for (String line : card.split("\n")) {
                String[] cells = cells(line);
                if (cells.length >= 5 && cells[0].matches("S-[0-9]+")) {
                    total++;
                    if (cells[4].equals("done")) {
                        done++;
                    } else if (next == null) {
                        next = cells[0] + " · " + cells[1];
                    }
                }
            }
            return "; подшагов done " + done + " из " + total + (next == null ? "" : ", следующий " + next);
        } catch (IOException e) {
            return "; карточки units/" + unit.id + ".md нет";
        }
    }

    private static boolean depsDone(Unit unit, List<Unit> units, Set<String> archived, boolean core) {
        for (String dep : unit.deps) {
            if (!depSatisfied(dep, units, archived, core)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Зависимость выполнена: юнит done или в архиве. При scope: core юнит tech считается
     * выполненным, когда сделаны его подшаги разбор, env и core: usage, cleanup и review при
     * этом объёме не делаются, и ждать их полного done - значит заблокировать следующую технологию.
     */
    private static boolean depSatisfied(String dep, List<Unit> units, Set<String> archived, boolean core) {
        if (archived.contains(dep)) {
            return true;
        }
        Unit depUnit = find(units, dep);
        if (depUnit == null) {
            return false;
        }
        if (depUnit.status.equals("done")) {
            return true;
        }
        return core && depUnit.type.equals("tech") && coreStepsLeft(dep) == 0;
    }

    private static Unit find(List<Unit> units, String id) {
        for (Unit unit : units) {
            if (unit.id.equals(id)) {
                return unit;
            }
        }
        return null;
    }

    private static void mapSizeNote(String text) {
        long lines = text.lines().count();
        if (lines > 600) {
            System.out.println("ЗАМЕТКА: карта " + lines + " строк - в итоговом ответе предложи: «напишите: сожми карту»");
        }
    }

    private static Map<String, String> frontMatter(String text) {
        Map<String, String> head = new LinkedHashMap<>();
        String[] lines = text.split("\n");
        if (lines.length == 0 || !lines[0].trim().equals("---")) {
            return head;
        }
        for (int i = 1; i < lines.length && !lines[i].trim().equals("---"); i++) {
            int colon = lines[i].indexOf(':');
            if (colon > 0) {
                head.put(lines[i].substring(0, colon).trim(), lines[i].substring(colon + 1).trim());
            }
        }
        return head;
    }

    private static String section(String text, String number) {
        Matcher start = Pattern.compile("(?m)^## " + Pattern.quote(number)).matcher(text);
        if (!start.find()) {
            return "";
        }
        Matcher end = Pattern.compile("(?m)^## ").matcher(text);
        int stop = end.find(start.end()) ? end.start() : text.length();
        return text.substring(start.start(), stop);
    }

    private static String[] cells(String line) {
        String trimmed = line.trim();
        if (!trimmed.startsWith("|")) {
            return new String[0];
        }
        String[] raw = trimmed.substring(1).split("\\|");
        String[] cells = new String[raw.length];
        for (int i = 0; i < raw.length; i++) {
            cells[i] = raw[i].trim();
        }
        return cells;
    }

    private static int parseInt(String value) {
        try {
            return Integer.parseInt(value.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    /** Агенты кита -> .gigacode/agents/ проекта. Возвращает имена файлов, которые записаны сейчас. */
    private static List<String> installAgents() throws IOException {
        Path skill = skillDir();
        Path source = skill == null ? null : skill.resolve("agents");
        if (source == null || !Files.isDirectory(source)) {
            System.out.println("ЗАМЕТКА: не нашёл каталог agents скилла orchestrator - агенты pvatf-* не проверены;"
                    + " запускай как java <каталог скилла>/scripts/NextAction.java");
            return List.of();
        }
        List<Path> files;
        try (Stream<Path> listing = Files.list(source)) {
            files = listing.filter(file -> file.getFileName().toString().endsWith(".md")).sorted().collect(Collectors.toList());
        }
        Path homeAgents = Paths.get(System.getProperty("user.home"), ".gigacode", "agents");
        List<String> written = new ArrayList<>();
        for (Path file : files) {
            String name = file.getFileName().toString();
            byte[] content = Files.readAllBytes(file);
            String expected = normalized(content);
            Path target = AGENTS.resolve(name);
            if (Files.exists(target) && normalized(Files.readAllBytes(target)).equals(expected)) {
                continue;
            }
            // такой же агент уже стоит у пользователя и в проекте его нет - GigaCode его видит
            Path inHome = homeAgents.resolve(name);
            if (!Files.exists(target) && Files.exists(inHome) && normalized(Files.readAllBytes(inHome)).equals(expected)) {
                continue;
            }
            boolean existed = Files.exists(target);
            Files.createDirectories(AGENTS);
            Files.write(target, content);
            written.add(name + (existed ? " (обновлён: текст отличался)" : " (новый)"));
        }
        return written;
    }

    /** Текст агента без BOM, \r и пробелов в конце строк: так копия с другими переводами строк не считается другой. */
    private static String normalized(byte[] content) {
        String text = new String(content, StandardCharsets.UTF_8);
        if (text.startsWith("\uFEFF")) {
            text = text.substring(1);
        }
        return text.replace("\r", "").replaceAll("[ \t]+\n", "\n").strip();
    }

    /** Каталог скилла: родитель каталога scripts, где лежит этот файл. */
    private static Path skillDir() {
        for (String argument : ProcessHandle.current().info().arguments().orElse(new String[0])) {
            if (argument.endsWith("NextAction.java")) {
                return Paths.get(argument).toAbsolutePath().getParent().getParent();
            }
        }
        Path inProject = Paths.get(".gigacode", "skills", "orchestrator").toAbsolutePath();
        if (Files.isDirectory(inProject.resolve("agents"))) {
            return inProject;
        }
        Path inHome = Paths.get(System.getProperty("user.home"), ".gigacode", "skills", "orchestrator");
        return Files.isDirectory(inHome.resolve("agents")) ? inHome : null;
    }

    private static void say(String action, String why) {
        System.out.println("ДЕЙСТВИЕ: " + action);
        System.out.println("ПОЧЕМУ: " + why);
    }
}
