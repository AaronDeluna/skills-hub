import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Помощник исполнителя юнита (скилл migration-step). Запуск из корня мигрируемого проекта:
 *
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Unit.java recite M-007 [S-04]   - что делаю сейчас (напоминание)
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Unit.java rules  M-007 [S-04]   - правила подшага в tmp/rules-now.md
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Unit.java check  M-007 [S-04]   - самопроверка правил кода и границ + классификатор
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Unit.java classify M-007 [S-04] - только классификатор
 *
 * Подшаг не указан - берётся первый подшаг юнита со статусом не done.
 * Нужна только Java 17+, внешних команд (grep, awk) не использует, кроме git в check.
 * Классификатор - Jev (polza.ai, System One API): ключ POLZA_AI_API_KEY или
 * ~/.gigacode/pvatf-classifier.properties (key, url, model, threshold). Не настроен - check работает без него.
 */
public class Unit {

    private static final Path MIGRATION = Paths.get(".gigacode", "data", "migration");

    public static void main(String[] args) throws Exception {
        System.setOut(new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8));
        if (args.length < 2) {
            System.out.println("Использование: java Unit.java <recite|rules|check|classify> M-<nnn> [S-<nn>]");
            System.exit(2);
        }
        String command = args[0];
        Path cardPath = MIGRATION.resolve("units").resolve(args[1] + ".md");
        if (!Files.exists(cardPath)) {
            System.out.println("НЕТ КАРТОЧКИ " + cardPath + " - проверь ID юнита (раздел 4 карты) и что запускаешь из корня проекта, где лежит .gigacode/");
            System.exit(2);
        }
        Card card = Card.read(cardPath);
        Step step = card.step(args.length > 2 ? args[2] : null);
        if (command.equals("recite")) {
            recite(card, step);
        } else if (command.equals("rules")) {
            System.exit(rules(card, step, true));
        } else if (command.equals("check")) {
            System.exit(check(card, step));
        } else if (command.equals("classify")) {
            System.exit(classify(card, step) == 0 ? 0 : 1);
        } else {
            System.out.println("Неизвестная команда: " + command);
            System.exit(2);
        }
    }

    // ---------- recite ----------

    private static void recite(Card card, Step step) throws IOException {
        System.out.println("=== СЕЙЧАС ===");
        System.out.println("Юнит " + card.id + " (" + card.type + ", " + card.tech + ")"
                + (step.id.isEmpty() ? "" : ", подшаг " + step.id + " · " + step.kind + " · " + step.title));
        if (!card.steps.isEmpty()) {
            long done = card.steps.stream().filter(s -> s.status.equals("done")).count();
            String next = "-";
            boolean passed = false;
            for (Step s : card.steps) {
                if (passed && !s.status.equals("done")) {
                    next = s.id + " · " + s.kind;
                    break;
                }
                if (s.id.equals(step.id)) {
                    passed = true;
                }
            }
            System.out.println("Подшагов done: " + done + " из " + card.steps.size() + "; следующий после этого: " + next);
        }
        System.out.println("Файлы (менять можно ТОЛЬКО их):");
        if (step.files.isEmpty()) {
            System.out.println("- нет (код не меняется)");
        }
        for (Map.Entry<String, String> file : step.files.entrySet()) {
            System.out.println("- " + file.getKey() + " (" + file.getValue() + ")");
        }
        System.out.println("Итоговый результат: " + oneLine(step.result));
        System.out.println("Чекпоинт: " + oneLine(step.checkpoint));
        List<String> ids = ruleIds(card, step);
        Set<String> docIds = new LinkedHashSet<>();
        Matcher d = Pattern.compile("\\bD-[a-z0-9-]+?-[0-9]+\\b").matcher(step.body);
        while (d.find()) {
            docIds.add(d.group());
        }
        System.out.println("Конспект подшага: " + (docIds.isEmpty() ? "-" : String.join(", ", docIds))
                + "  (текст - в tmp/docs-now.md после Unit.java rules; поиск по конспекту - Notes.java find " + card.tech + " <слова>)");
        System.out.println("Правила подшага: " + String.join(", ", ids)
                + "  (текст: java -Dfile.encoding=UTF-8 .gigacode/skills/migration-step/scripts/Unit.java rules " + card.id + " " + step.id + ")");
        System.out.println("Порядок: правила -> правки по «Что сделать» -> Unit.java check (с классификатором) -> проверяющий -> чекпоинт -> коммит");
        System.out.println("Нельзя: вопросы человеку; файлы не из списка; DTO ответа; свои matchers и списки matchers;"
                + " делегаты и вложенные классы; имена фрейма не из «Таблицы подтверждений».");
    }

    // ---------- rules ----------

    /** @return 0 - все номера найдены; 1 - какого-то правила нет в code-rules.md (номер в карточке с ошибкой). */
    private static int rules(Card card, Step step, boolean print) throws IOException {
        Path codeRules = skillDir().resolve("references").resolve("code-rules.md");
        String text = Files.readString(codeRules, StandardCharsets.UTF_8);
        List<String> ids = ruleIds(card, step);
        StringBuilder out = new StringBuilder();
        out.append("# Правила подшага ").append(card.id).append(' ').append(step.id).append(" (").append(step.kind).append(")\n\n");
        Set<String> found = new LinkedHashSet<>();
        String[] lines = text.split("\n", -1);
        boolean copying = false;
        for (String line : lines) {
            Matcher rule = Pattern.compile("^- \\*\\*(MR-[0-9H]+) ·").matcher(line);
            if (rule.find()) {
                copying = ids.contains(rule.group(1));
                if (copying) {
                    found.add(rule.group(1));
                }
            } else if (line.startsWith("## ") || line.startsWith("---")) {
                copying = false;
            }
            if (copying) {
                out.append(line).append('\n');
            }
        }
        Matcher human = Pattern.compile("(?m)^## Правила: добавлено человеком").matcher(text);
        if (human.find()) {
            out.append('\n').append(text.substring(human.start()));
        }
        Path target = MIGRATION.resolve("tmp").resolve("rules-now.md");
        Files.createDirectories(target.getParent());
        Files.writeString(target, out.toString(), StandardCharsets.UTF_8);
        int docs = writeDocs(card, step);
        List<String> missing = new ArrayList<>(ids);
        missing.removeAll(found);
        if (ids.isEmpty()) {
            missing.add("(номеров нет ни в карточке, ни в substep-rules.md для вида " + step.kind + ")");
        }
        if (print) {
            System.out.println("Записано в " + target + ": " + found.size() + " правил - " + String.join(", ", found));
            if (!missing.isEmpty()) {
                System.out.println("ОШИБКА: не найдены в code-rules.md: " + String.join(", ", missing)
                        + " - исправь номера в карточке (таблица - references/substep-rules.md), потом запусти снова");
            }
            System.out.println("Записи конспекта подшага: " + docs + " - в .gigacode/data/migration/tmp/docs-now.md");
            System.out.println("Прочитай оба файла целиком перед правками. Нужного имени фрейма там нет -> сначала Notes.java find, потом сабагент документации.");
        }
        return missing.isEmpty() ? 0 : 1;
    }

    /** Записи конспекта, на которые ссылается подшаг и «Таблица подтверждений», - в tmp/docs-now.md. */
    private static int writeDocs(Card card, Step step) throws IOException {
        Set<String> ids = new LinkedHashSet<>();
        Matcher m = Pattern.compile("\\bD-[a-z0-9-]+?-[0-9]+\\b").matcher(step.body + "\n" + card.confirmations);
        while (m.find()) {
            ids.add(m.group());
        }
        StringBuilder out = new StringBuilder("# Записи конспекта подшага " + card.id + " " + step.id + "\n\n");
        int found = 0;
        Path notes = MIGRATION.resolve("doc-notes");
        for (String id : ids) {
            String tech = id.substring(2, id.lastIndexOf('-'));
            Path file = notes.resolve(tech + ".md");
            String record = Files.exists(file) ? record(Files.readString(file, StandardCharsets.UTF_8), id) : null;
            if (record == null) {
                out.append("## ").append(id).append(" - НЕТ В КОНСПЕКТЕ (ссылка в карточке есть, записи нет)\n\n");
            } else {
                out.append(record).append('\n');
                found++;
            }
        }
        Path target = MIGRATION.resolve("tmp").resolve("docs-now.md");
        Files.createDirectories(target.getParent());
        Files.writeString(target, out.toString(), StandardCharsets.UTF_8);
        return found;
    }

    private static String record(String notes, String id) {
        Matcher start = Pattern.compile("(?m)^#{2,3} " + Pattern.quote(id) + "\\b").matcher(notes);
        if (!start.find()) {
            return null;
        }
        Matcher next = Pattern.compile("(?m)^#{1,3} ").matcher(notes);
        int end = next.find(start.end()) ? next.start() : notes.length();
        return notes.substring(start.start(), end);
    }

    /** Номера правил: из карточки, иначе - по виду подшага из таблицы references/substep-rules.md. */
    private static List<String> ruleIds(Card card, Step step) throws IOException {
        List<String> ids = new ArrayList<>();
        Matcher m = Pattern.compile("MR-[0-9H]+").matcher(step.rules);
        while (m.find()) {
            ids.add(m.group());
        }
        if (!ids.isEmpty()) {
            return ids;
        }
        String kind = step.kind;
        String text = Files.readString(skillDir().resolve("references").resolve("substep-rules.md"), StandardCharsets.UTF_8);
        for (String line : text.split("\n")) {
            if (!line.startsWith("| `")) {
                continue;
            }
            String[] cells = line.split("\\|");
            if (cells.length < 3) {
                continue;
            }
            String head = cells[1];
            boolean match = head.contains("`" + kind + "`");
            if (kind.equals("core")) {
                match = head.contains("`core`") && head.contains(card.coreMode.equals("in-place") ? "in-place" : "new");
            }
            if (match) {
                Matcher r = Pattern.compile("MR-[0-9H]+").matcher(cells[2]);
                while (r.find()) {
                    ids.add(r.group());
                }
                if (kind.equals("core") && card.coreMode.equals("in-place")) {
                    ids.addAll(List.of("MR-12", "MR-13", "MR-24", "MR-30", "MR-32", "MR-41", "MR-43", "MR-49", "MR-50"));
                }
            }
        }
        Path map = MIGRATION.resolve("MIGRATION-MAP.md");
        boolean flow = Files.exists(map)
                && Pattern.compile("(?m)^- Стиль шагов: flow").matcher(Files.readString(map, StandardCharsets.UTF_8)).find();
        if (flow && (kind.equals("core") || kind.equals("usage")) && !ids.contains("MR-44")) {
            ids.add("MR-44");
        }
        return ids;
    }

    // ---------- check ----------

    private static final String[][] FILE_CHECKS = {
        {"MR-33", "(^|[^A-Za-z0-9_])var +[A-Za-z_][A-Za-z0-9_]* *(=|:)", "var вместо явного типа"},
        {"MR-29", "Assertions\\.|assert(Equals|True|False|NotNull|Null|That|All)\\(|SoftAssertions", "ассерт вместо matcher: замени на matcher; matcher нет в документации - запиши в «Сделано» подшага «исключение MR-29: <файл>:<строка>» и строку во «Входящие»"},
        {"MR-41", "\\.as\\([A-Z][A-Za-z0-9_]*\\.class\\)|readValue\\(|fromJson\\(|\\.getObject\\(|\\.extract\\(\\)", "ответ превращают в объект"},
        {"MR-4", "^(?!.*@ru\\.sber\\.qa\\.allure\\.system\\.System\\b)[^/*\"]*[^A-Za-z0-9_.\"](org|com|ru|io|java)\\.[a-z0-9_]+\\.[a-z0-9_.]+\\.[A-Z]", "полное имя класса в коде вместо import"},
        {"MR-43", "\\b(log|logger|LOG|LOGGER)\\.(info|debug|trace|warn|error)\\(|System\\.(out|err)\\.print|\\.log\\(\\)\\.(all|body|headers|ifValidationFails)|(Request|Response)LoggingFilter|\\.prettyPrint\\(|\\.prettyPeek\\(|\\.peek\\(", "ручное логирование (остаётся только ход сценария)"},
        {"MR-48", "implements [A-Za-z.]*(Matcher|Condition)\\b|List<[A-Za-z.]*Matcher>|matchers\\.add\\(|\\.toArray\\(new [A-Za-z.]*Matcher|static [A-Za-z.<>]*(Matcher|Condition) [a-z][A-Za-z0-9]*\\(", "своя конструкция вокруг matcher"},
        {"MR-48", "getRestHistory\\(\\)\\.getLast\\(\\)|JacksonHelper|JsonNode|\\.path\\(\"|textOrNull|intOrNull|longOrNull|boolOrNull|compareNumbers|assertDatesEqual|bigDecimalsEqual", "ответ разбирают руками или своими хелперами"},
        {"MR-48", "equalToText\\(String\\.valueOf|equalToText\\([^)]*\\.toString\\(\\)", "число или дата проверяются как текст"},
        {"MR-48", "assertAll\\(", "assertAll: группа проверок - .shouldSoft(...)"},
        {"MR-49", "^\\s+(public |private |protected )?(static )?(final )?(class|interface|enum|record) [A-Z]", "вложенный класс"},
        {"MR-49", "^\\s+return [A-Z][A-Za-z0-9]*\\.[a-z][A-Za-z0-9]*\\([a-zA-Z, ]*\\);", "метод-делегат: перевести вызывающих на настоящий метод"},
        {"MR-47", "ConfigFactory\\.create|new Properties\\(\\)|getResourceAsStream\\(|ResourceBundle\\.getBundle|System\\.(getProperty|getenv)\\(|@Value\\(|PropertiesLoader|ConfigReader|PropertyReader", "своё чтение настроек"},
        {"MR-45", "(^|[ .(])[a-z][A-Za-z0-9]*_[A-Za-z0-9_]*( *\\(| *=| *;|,|\\))", "имя с нижним подчёркиванием"},
        {"MR-14", "Thread\\.sleep|TimeUnit\\.[A-Z]+\\.sleep", "sleep вместо ожидания фрейма"},
        {"MR-21", "\\b(TODO|FIXME)\\b", "TODO/FIXME в коде"},
    };

    private static final String[][] TEST_CLASS_CHECKS = {
        {"MR-46", "@ExtendWith\\(PerfeccionistaExtension|@SetEnvironmentConfiguration", "аннотации фрейма на тест-классе (место - базовый тест-класс)"},
        {"MR-42", "^\\s*(private|protected|static) [^=]*\\([^)]*\\)\\s*(throws [A-Za-z, ]+)?\\{", "вспомогательный метод в тест-классе (место - класс шагов)"},
    };

    private static int check(Card card, Step step) throws IOException, InterruptedException {
        int findings = 0;
        System.out.println("CHECK " + card.id + " " + step.id + " (" + step.kind + "), файлов: " + step.files.size());
        Set<String> exceptions = exceptions(step);
        for (Map.Entry<String, String> entry : step.files.entrySet()) {
            Path file = Paths.get(entry.getKey());
            if (entry.getValue().contains("удал")) {
                if (Files.exists(file)) {
                    System.out.println("ИТОГ " + file + ": файл должен быть удалён, но есть");
                    findings++;
                }
                continue;
            }
            if (!Files.exists(file)) {
                System.out.println("ИТОГ " + file + ": файла нет");
                findings++;
                continue;
            }
            if (file.toString().matches(".*\\.(properties|ya?ml)$")) {
                findings += checkSettings(file);
                continue;
            }
            if (!file.toString().endsWith(".java") && !file.toString().endsWith(".kt")) {
                continue;
            }
            List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
            findings += scan(file, lines, FILE_CHECKS, exceptions);
            if (lines.stream().anyMatch(l -> l.matches("\\s*@Test\\b.*"))) {
                findings += scan(file, lines, TEST_CLASS_CHECKS, exceptions);
            }
            findings += checkSetters(file, lines);
            findings += checkServiceLookups(file, lines);
        }
        findings += checkBoundaries(step);
        if (findings > 0) {
            System.out.println("КЛАССИФИКАТОР: пропущен - сначала исправь находки выше");
        } else {
            findings += classify(card, step);
        }
        System.out.println("ИТОГ: находок " + findings + (findings == 0 ? " - чисто" : " - исправь и запусти снова"));
        return findings == 0 ? 0 : 1;
    }

    /** Файл настроек: у каждого ключа есть значение, заглушек нет (MR-47, значения - из CONNECTIONS.md). */
    private static int checkSettings(Path file) throws IOException {
        int found = 0;
        List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
        Pattern empty = Pattern.compile("^\\s*[^#!\\s][^=:]*[=:]\\s*$");
        Pattern stub = Pattern.compile("(?i)TODO|changeme|change_me|<[^>]+>|\"\"\\s*$");
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i);
            if (line.trim().startsWith("#") || line.trim().startsWith("!")) {
                continue;
            }
            boolean yamlParent = file.toString().matches(".*\\.ya?ml$") && line.trim().endsWith(":")
                    && i + 1 < lines.size() && indent(lines.get(i + 1)) > indent(line);
            if ((empty.matcher(line).matches() && !yamlParent) || stub.matcher(line).find()) {
                System.out.println("MR-47 " + file + ":" + (i + 1) + " - ключ без значения или заглушка (значение - из CONNECTIONS.md): " + line.trim());
                found++;
            }
        }
        return found;
    }

    private static int indent(String line) {
        int n = 0;
        while (n < line.length() && line.charAt(n) == ' ') {
            n++;
        }
        return n;
    }

    /**
     * Разрешённые исключения подшага: строка «исключение MR-29: <файл>:<строка>» в его разделе
     * карточки. MR-29 разрешает стандартный ассерт, если matcher нет в документации (и есть
     * строка во «Входящие»); другие правила исключений не имеют.
     */
    private static Set<String> exceptions(Step step) {
        Set<String> allowed = new LinkedHashSet<>();
        Matcher m = Pattern.compile("исключение (MR-29): `?([^`\\s:]+):([0-9]+)").matcher(step.body);
        while (m.find()) {
            allowed.add(m.group(1) + " " + m.group(2) + ":" + m.group(3));
        }
        return allowed;
    }

    private static int scan(Path file, List<String> lines, String[][] checks, Set<String> exceptions) {
        int count = 0;
        boolean inBlockComment = false;
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i);
            String trimmed = line.trim();
            if (trimmed.startsWith("/*")) {
                inBlockComment = true;
            }
            boolean comment = inBlockComment || trimmed.startsWith("//") || trimmed.startsWith("*")
                    || trimmed.startsWith("import ") || trimmed.startsWith("package ");
            if (trimmed.contains("*/")) {
                inBlockComment = false;
            }
            for (String[] check : checks) {
                boolean commentAllowed = check[0].equals("MR-21");
                if (comment && !commentAllowed) {
                    continue;
                }
                if (Pattern.compile(check[1]).matcher(line).find()) {
                    if (check[0].equals("MR-49") && check[2].startsWith("вложенный") && isBuilder(line)) {
                        continue;
                    }
                    if (exceptions.contains(check[0] + " " + file.toString().replace('\\', '/') + ":" + (i + 1))) {
                        continue;
                    }
                    System.out.println(check[0] + " " + file + ":" + (i + 1) + " - " + check[2] + ": " + trimmed);
                    count++;
                }
            }
        }
        return count;
    }

    private static boolean isBuilder(String line) {
        return line.matches(".*static (final )?class [A-Za-z]*Builder\\b.*");
    }

    /** MR-34: 4 и более setXxx подряд на одну переменную. */
    private static int checkSetters(Path file, List<String> lines) {
        Pattern setter = Pattern.compile("^\\s*([a-z][A-Za-z0-9]*)\\.set[A-Z][A-Za-z0-9]*\\(");
        String current = null;
        int run = 0;
        int start = 0;
        int count = 0;
        for (int i = 0; i <= lines.size(); i++) {
            Matcher m = i < lines.size() ? setter.matcher(lines.get(i)) : null;
            String variable = m != null && m.find() ? m.group(1) : null;
            if (variable != null && variable.equals(current)) {
                run++;
                continue;
            }
            if (run >= 4) {
                System.out.println("MR-34 " + file + ":" + (start + 1) + " - сеттеров подряд на " + current + ": " + run + ", нужен билдер");
                count++;
            }
            current = variable;
            run = variable == null ? 0 : 1;
            start = i;
        }
        return count;
    }

    /** MR-35: getForCurrentThread() чаще, чем разных сервисов в файле. */
    private static int checkServiceLookups(Path file, List<String> lines) {
        int lookups = 0;
        Set<String> services = new LinkedHashSet<>();
        Pattern service = Pattern.compile("getService\\(([A-Za-z0-9_]+)\\.class\\)");
        for (String line : lines) {
            if (line.contains("getForCurrentThread()")) {
                lookups++;
            }
            Matcher m = service.matcher(line);
            while (m.find()) {
                services.add(m.group(1));
            }
        }
        if (lookups > Math.max(1, services.size())) {
            System.out.println("MR-35 " + file + " - getForCurrentThread() " + lookups + " раз при " + services.size()
                    + " сервисах: получение сервиса - один приватный метод");
            return 1;
        }
        return 0;
    }

    /** Изменённые файлы вне списка подшага. */
    private static int checkBoundaries(Step step) throws IOException, InterruptedException {
        // -z: пути как есть (пробелы, кириллица); --untracked-files=all: новые файлы поимённо, а не каталогом
        Process process = new ProcessBuilder("git", "status", "--porcelain", "-z", "--untracked-files=all")
                .redirectErrorStream(true).start();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        process.waitFor();
        int count = 0;
        String[] entries = output.split("\0");
        for (int i = 0; i < entries.length; i++) {
            String entry = entries[i];
            if (entry.length() < 4) {
                continue;
            }
            String status = entry.substring(0, 2);
            String path = entry.substring(3);
            if (status.contains("R") || status.contains("C")) {
                i++; // следующая запись - старый путь переименования
            }
            if (path.startsWith(".gigacode/")) {
                continue;
            }
            if (!step.files.containsKey(path)) {
                System.out.println("ГРАНИЦЫ " + path + " - изменён, но его нет в файлах подшага: верни (git checkout -- " + path
                        + ") или допиши в карточку с пометкой «добавлен по ходу»");
                count++;
            }
        }
        return count;
    }


    // ---------- классификатор ----------

    private static final int CLASSIFIER_MAX_FILE = 80_000;

    /**
     * Классификатор Jev (polza.ai, System One API): каждый файл подшага (.java, .kt) - один запрос.
     * state - задача подшага, git diff файла, файл целиком с номерами строк; questions - по
     * вопросу «да/нет» (noul) на каждое правило подшага. Ответ - вероятность нарушения 0..1;
     * не меньше порога (по умолчанию 0.7) - находка. Нет ответа по правилу - находка
     * КЛАССИФИКАТОР. Ответ кешируется по телу запроса: неизменённый файл второй раз не
     * отправляется. Отчёт - tmp/classify.md.
     *
     * @return число находок (нарушения + ошибки классификатора)
     */
    private static int classify(Card card, Step step) throws IOException, InterruptedException {
        Map<String, String> config = classifierConfig();
        if (config.get("key").isEmpty()) {
            System.out.println("КЛАССИФИКАТОР: не настроен (POLZA_AI_API_KEY или ~/.gigacode/pvatf-classifier.properties) - пропущен");
            return 0;
        }
        Map<String, String> rules = ruleTexts(ruleIds(card, step));
        if (rules.isEmpty()) {
            System.out.println("КЛАССИФИКАТОР: у подшага нет правил MR - пропущен");
            return 0;
        }
        double threshold = Double.parseDouble(config.get("threshold"));
        String todo = Card.field(step.body, "Что сделать");
        Path cache = MIGRATION.resolve("tmp").resolve("classify-cache");
        Files.createDirectories(cache);
        StringBuilder report = new StringBuilder("# Классификатор " + card.id + " " + step.id + " (порог " + threshold + ")\n\n"
                + "| Файл | Правило | Вероятность нарушения | Итог |\n|------|---------|-----------------------|------|\n");
        int findings = 0;
        int files = 0;
        int requests = 0;
        int cached = 0;
        double cost = 0;
        for (Map.Entry<String, String> entry : step.files.entrySet()) {
            Path file = Paths.get(entry.getKey());
            String name = file.toString();
            if (entry.getValue().contains("удал") || !Files.exists(file) || !(name.endsWith(".java") || name.endsWith(".kt"))) {
                continue;
            }
            files++;
            List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
            StringBuilder numbered = new StringBuilder();
            for (int i = 0; i < lines.size(); i++) {
                numbered.append(i + 1).append(": ").append(lines.get(i)).append('\n');
            }
            String content = numbered.length() > CLASSIFIER_MAX_FILE
                    ? "(файл больше " + CLASSIFIER_MAX_FILE + " символов - смотри только file.diff)" : numbered.toString();
            String diff = git("diff", "HEAD", "--", entry.getKey());
            if (diff.isBlank()) {
                diff = git("ls-files", "--", entry.getKey()).isBlank()
                        ? "(файл создан в этом подшаге: изменения - весь файл)" : "(изменений нет)";
            }
            StringBuilder body = new StringBuilder("{\"model\":").append(Json.quote(config.get("model")))
                    .append(",\"state\":{\"task\":{\"result\":").append(Json.quote(oneLine(step.result)))
                    .append(",\"todo\":").append(Json.quote(todo.isEmpty() ? "-" : todo))
                    .append("},\"file\":{\"path\":").append(Json.quote(entry.getKey()))
                    .append(",\"diff\":").append(Json.quote(diff))
                    .append(",\"content\":").append(Json.quote(content)).append("}},\"questions\":{");
            boolean first = true;
            for (Map.Entry<String, String> rule : rules.entrySet()) {
                body.append(first ? "" : ",").append(Json.quote(rule.getKey())).append(":{\"type\":\"noul\",\"instructions\":")
                        .append(Json.quote("Код в `file.content` нарушает правило ниже? Правило действует на весь файл; "
                                + "`task` - что должен был сделать этот шаг, `file.diff` - что в файле изменено.\n" + rule.getValue()))
                        .append(",\"criteria\":{\"true\":").append(Json.quote("В файле есть код, который прямо нарушает это правило, и можно назвать его строку"))
                        .append(",\"false\":").append(Json.quote("Нарушения нет, правило не про такой код или нарушение только предполагается"))
                        .append("}}");
                first = false;
            }
            body.append("}}");
            Path cachedAnswer = cache.resolve(sha256(body.toString()) + ".json");
            String answer;
            if (Files.exists(cachedAnswer)) {
                answer = Files.readString(cachedAnswer, StandardCharsets.UTF_8);
                cached++;
            } else {
                try {
                    answer = askClassifier(config, body.toString());
                    requests++;
                } catch (IOException e) {
                    System.out.println("КЛАССИФИКАТОР " + name + " - ошибка запроса: "
                            + oneLine(e.getMessage() == null ? e.toString() : e.getMessage())
                            + " (запусти check ещё раз; повторилось - строка «решить человеку» во «Входящие»)");
                    findings++;
                    continue;
                }
            }
            Map<?, ?> answers;
            try {
                Map<?, ?> root = (Map<?, ?>) new Json(answer).value();
                answers = (Map<?, ?>) root.get("answers");
                Object usage = root.get("usage");
                Object rub = usage instanceof Map ? ((Map<?, ?>) usage).get("cost_rub") : null;
                if (rub != null && !Files.exists(cachedAnswer)) {
                    cost += Double.parseDouble(rub.toString());
                }
            } catch (RuntimeException e) {
                System.out.println("КЛАССИФИКАТОР " + name + " - ответ не в формате System One: " + e
                        + " (запусти check ещё раз; повторилось - строка «решить человеку» во «Входящие»)");
                findings++;
                continue;
            }
            boolean complete = true;
            for (String id : rules.keySet()) {
                Object a = answers == null ? null : answers.get(id);
                Object p = a instanceof Map ? ((Map<?, ?>) a).get("noul") : null;
                if (p == null) {
                    System.out.println("КЛАССИФИКАТОР " + name + " - нет ответа по " + id + " (запусти check ещё раз)");
                    report.append("| ").append(name).append(" | ").append(id).append(" | - | нет ответа |\n");
                    findings++;
                    complete = false;
                    continue;
                }
                double probability = Double.parseDouble(p.toString());
                boolean violated = probability >= threshold;
                report.append("| ").append(name).append(" | ").append(id).append(" | ")
                        .append(String.format(java.util.Locale.ROOT, "%.2f", probability)).append(" | ")
                        .append(violated ? "нарушено" : "нет").append(" |\n");
                if (violated) {
                    System.out.println(id + " " + name + " - классификатор: нарушено правило «" + ruleTitle(rules.get(id))
                            + "», вероятность " + String.format(java.util.Locale.ROOT, "%.2f", probability)
                            + " - найди место по правилу и исправь");
                    findings++;
                }
            }
            if (complete && !Files.exists(cachedAnswer)) {
                Files.writeString(cachedAnswer, answer, StandardCharsets.UTF_8);
            }
        }
        Path target = MIGRATION.resolve("tmp").resolve("classify.md");
        Files.writeString(target, report.toString(), StandardCharsets.UTF_8);
        System.out.println("КЛАССИФИКАТОР: файлов " + files + ", правил " + rules.size() + ", запросов " + requests
                + ", из кеша " + cached + ", находок " + findings
                + (cost > 0 ? String.format(java.util.Locale.ROOT, ", стоимость %.4f руб.", cost) : "")
                + " (ответы - " + target + ")");
        return findings;
    }

    /** Название правила: текст между «MR-n · » и закрывающими «**». */
    private static String ruleTitle(String rule) {
        Matcher m = Pattern.compile("^- \\*\\*MR-[0-9H]+ · (.*?)\\.?\\*\\*").matcher(rule);
        return m.find() ? m.group(1) : rule.lines().findFirst().orElse("");
    }

    /** Тексты правил из code-rules.md: от «- **MR-n ·» до следующего правила или заголовка. */
    private static Map<String, String> ruleTexts(List<String> ids) throws IOException {
        String text = Files.readString(skillDir().resolve("references").resolve("code-rules.md"), StandardCharsets.UTF_8);
        Map<String, String> rules = new LinkedHashMap<>();
        String current = null;
        StringBuilder body = new StringBuilder();
        for (String line : (text + "\n## конец").split("\n", -1)) {
            Matcher rule = Pattern.compile("^- \\*\\*(MR-[0-9H]+) ·").matcher(line);
            boolean end = rule.find() || line.startsWith("## ") || line.startsWith("---");
            if (end && current != null) {
                rules.put(current, body.toString().trim());
                current = null;
            }
            if (rule.find(0) && ids.contains(rule.group(1)) && !rules.containsKey(rule.group(1))) {
                current = rule.group(1);
                body.setLength(0);
            }
            if (current != null) {
                body.append(line).append('\n');
            }
        }
        Map<String, String> ordered = new LinkedHashMap<>();
        for (String id : ids) {
            if (rules.containsKey(id)) {
                ordered.put(id, rules.get(id));
            }
        }
        return ordered;
    }

    /**
     * Настройки: переменные окружения POLZA_AI_API_KEY (или PVATF_CLASSIFIER_KEY), PVATF_CLASSIFIER_URL,
     * PVATF_CLASSIFIER_MODEL, PVATF_CLASSIFIER_THRESHOLD, иначе ~/.gigacode/pvatf-classifier.properties
     * (key, url, model, threshold).
     */
    private static Map<String, String> classifierConfig() throws IOException {
        java.util.Properties file = new java.util.Properties();
        Path path = Paths.get(System.getProperty("user.home"), ".gigacode", "pvatf-classifier.properties");
        if (Files.exists(path)) {
            try (var reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
                file.load(reader);
            }
        }
        Map<String, String> defaults = Map.of("key", "", "url", "https://polza.ai/api/v1/systemone",
                "model", "typesafe/jev", "threshold", "0.7");
        Map<String, String> config = new LinkedHashMap<>();
        for (String key : List.of("key", "url", "model", "threshold")) {
            String env = System.getenv("PVATF_CLASSIFIER_" + key.toUpperCase());
            if ((env == null || env.isBlank()) && key.equals("key")) {
                env = System.getenv("POLZA_AI_API_KEY");
            }
            String value = env != null && !env.isBlank() ? env : file.getProperty(key, defaults.get(key));
            config.put(key, value.trim());
        }
        if (!config.get("threshold").matches("0?\\.[0-9]+|1(\\.0+)?")) {
            config.put("threshold", "0.7");
        }
        return config;
    }

    /** Один запрос System One; возвращает тело ответа (JSON). */
    private static String askClassifier(Map<String, String> config, String body) throws IOException, InterruptedException {
        java.net.http.HttpRequest request = java.net.http.HttpRequest.newBuilder(java.net.URI.create(config.get("url")))
                .timeout(java.time.Duration.ofSeconds(180))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + config.get("key"))
                .POST(java.net.http.HttpRequest.BodyPublishers.ofString(body, StandardCharsets.UTF_8))
                .build();
        java.net.http.HttpResponse<String> response = java.net.http.HttpClient.newBuilder()
                .connectTimeout(java.time.Duration.ofSeconds(30)).build()
                .send(request, java.net.http.HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() != 200) {
            String text = response.body();
            throw new IOException("HTTP " + response.statusCode() + ": " + text.substring(0, Math.min(300, text.length())));
        }
        return response.body();
    }

    private static String git(String... args) throws IOException, InterruptedException {
        List<String> command = new ArrayList<>(List.of("git"));
        command.addAll(List.of(args));
        Process process = new ProcessBuilder(command).redirectErrorStream(true).start();
        String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        process.waitFor();
        return output;
    }

    private static String sha256(String text) {
        try {
            byte[] hash = java.security.MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder();
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Минимальный JSON: строки, числа, объекты, массивы, true/false/null. */
    static final class Json {
        private final String s;
        private int i;

        Json(String s) {
            this.s = s;
        }

        static String quote(String text) {
            StringBuilder out = new StringBuilder("\"");
            for (char c : text.toCharArray()) {
                switch (c) {
                    case '"': out.append("\\\""); break;
                    case '\\': out.append("\\\\"); break;
                    case '\n': out.append("\\n"); break;
                    case '\r': out.append("\\r"); break;
                    case '\t': out.append("\\t"); break;
                    default:
                        if (c < 0x20) {
                            out.append(String.format("\\u%04x", (int) c));
                        } else {
                            out.append(c);
                        }
                }
            }
            return out.append('"').toString();
        }

        Object value() {
            skip();
            char c = s.charAt(i);
            if (c == '{') {
                Map<String, Object> map = new LinkedHashMap<>();
                i++;
                skip();
                if (s.charAt(i) == '}') {
                    i++;
                    return map;
                }
                while (true) {
                    skip();
                    String key = string();
                    skip();
                    i++; // ':'
                    map.put(key, value());
                    skip();
                    if (s.charAt(i++) == '}') {
                        return map;
                    }
                }
            }
            if (c == '[') {
                List<Object> list = new ArrayList<>();
                i++;
                skip();
                if (s.charAt(i) == ']') {
                    i++;
                    return list;
                }
                while (true) {
                    list.add(value());
                    skip();
                    if (s.charAt(i++) == ']') {
                        return list;
                    }
                }
            }
            if (c == '"') {
                return string();
            }
            int start = i;
            while (i < s.length() && ",}] \n\r\t".indexOf(s.charAt(i)) < 0) {
                i++;
            }
            String word = s.substring(start, i);
            return word.equals("null") ? null : word;
        }

        private String string() {
            StringBuilder out = new StringBuilder();
            i++; // '"'
            while (true) {
                char c = s.charAt(i++);
                if (c == '"') {
                    return out.toString();
                }
                if (c == '\\') {
                    char e = s.charAt(i++);
                    switch (e) {
                        case 'n': out.append('\n'); break;
                        case 'r': out.append('\r'); break;
                        case 't': out.append('\t'); break;
                        case 'b': out.append('\b'); break;
                        case 'f': out.append('\f'); break;
                        case 'u': out.append((char) Integer.parseInt(s.substring(i, i + 4), 16)); i += 4; break;
                        default: out.append(e);
                    }
                } else {
                    out.append(c);
                }
            }
        }

        private void skip() {
            while (i < s.length() && Character.isWhitespace(s.charAt(i))) {
                i++;
            }
        }
    }

    // ---------- helpers ----------

    private static String oneLine(String text) {
        String compact = text.replaceAll("\\s+", " ").trim();
        return compact.isEmpty() ? "-" : compact;
    }

    /** Каталог скилла: родитель каталога scripts, где лежит этот файл. */
    static Path skillDir() {
        for (String argument : ProcessHandle.current().info().arguments().orElse(new String[0])) {
            if (argument.endsWith("Unit.java")) {
                Path script = Paths.get(argument).toAbsolutePath();
                return script.getParent().getParent();
            }
        }
        Path inProject = Paths.get(".gigacode", "skills", "migration-step").toAbsolutePath();
        if (Files.exists(inProject.resolve("references").resolve("code-rules.md"))) {
            return inProject;
        }
        Path fallback = Paths.get(System.getProperty("user.home"), ".gigacode", "skills", "migration-step");
        if (Files.exists(fallback)) {
            return fallback;
        }
        throw new IllegalStateException("Не нашёл каталог скилла migration-step: запускай как java <каталог скилла>/scripts/Unit.java");
    }

    // ---------- карточка ----------

    static final class Step {
        String id = "";
        String kind = "";
        String title = "";
        String status = "";
        Map<String, String> files = new LinkedHashMap<>();
        String result = "";
        String checkpoint = "";
        String rules = "";
        String body = "";
    }

    static final class Card {
        String id;
        String type;
        String tech;
        String coreMode;
        List<Step> steps = new ArrayList<>();
        Step whole = new Step();
        String confirmations = "";

        static Card read(Path path) throws IOException {
            if (!Files.exists(path)) {
                throw new IllegalArgumentException("Нет карточки " + path);
            }
            String text = Files.readString(path, StandardCharsets.UTF_8);
            Card card = new Card();
            card.id = front(text, "id");
            card.type = front(text, "type");
            card.tech = front(text, "tech");
            card.coreMode = front(text, "core_mode");
            Map<String, String> sections = sections(text);
            String table = sections.getOrDefault("Подшаги", "");
            for (String line : table.split("\n")) {
                String[] cells = cells(line);
                if (cells.length >= 5 && cells[0].matches("S-[0-9]+")) {
                    Step step = new Step();
                    step.id = cells[0];
                    step.kind = cells[1];
                    step.title = cells[2];
                    step.status = cells[4];
                    card.steps.add(step);
                }
            }
            for (Step step : card.steps) {
                for (Map.Entry<String, String> section : sections.entrySet()) {
                    if (section.getKey().startsWith(step.id + " ")) {
                        fill(step, section.getValue());
                    }
                }
            }
            Step whole = card.whole;
            whole.kind = card.type;
            whole.title = text.lines().filter(l -> l.startsWith("# ")).findFirst().orElse("").replaceFirst("^# ", "");
            whole.files = fileTable(sections.getOrDefault("Файлы юнита", ""));
            whole.result = sections.getOrDefault("Цель", "");
            whole.checkpoint = sections.getOrDefault("Критерии готовности", "");
            whole.rules = sections.getOrDefault("Правила юнита", "");
            whole.body = text;
            int confirmStart = text.indexOf("### Таблица подтверждений");
            if (confirmStart >= 0) {
                int next = text.indexOf("\n#", confirmStart + 5);
                card.confirmations = text.substring(confirmStart, next > 0 ? next : text.length());
            }
            return card;
        }

        Step step(String id) {
            if (steps.isEmpty()) {
                return whole;
            }
            for (Step step : steps) {
                if (id != null ? step.id.equals(id) : !step.status.equals("done")) {
                    return step;
                }
            }
            if (id != null) {
                throw new IllegalArgumentException("В карточке " + this.id + " нет подшага " + id);
            }
            throw new IllegalArgumentException("В карточке " + this.id + " все подшаги done");
        }

        private static void fill(Step step, String body) {
            step.body = body;
            step.files = fileTable(body);
            step.result = field(body, "Итоговый результат");
            step.checkpoint = field(body, "Чекпоинт");
            step.rules = field(body, "Правила подшага");
        }

        static String front(String text, String key) {
            Matcher m = Pattern.compile("(?m)^" + key + ":\\s*(.*)$").matcher(text);
            return m.find() ? m.group(1).trim() : "-";
        }

        static Map<String, String> sections(String text) {
            Map<String, String> result = new LinkedHashMap<>();
            String name = null;
            StringBuilder body = new StringBuilder();
            for (String line : text.split("\n", -1)) {
                if (line.startsWith("## ")) {
                    if (name != null) {
                        result.put(name, body.toString());
                    }
                    name = line.substring(3).trim();
                    body.setLength(0);
                } else if (name != null) {
                    body.append(line).append('\n');
                }
            }
            if (name != null) {
                result.put(name, body.toString());
            }
            return result;
        }

        /** Значение поля «- Имя: ...» до следующего поля «- X:» верхнего уровня. */
        static String field(String body, String name) {
            StringBuilder value = new StringBuilder();
            boolean in = false;
            for (String line : body.split("\n")) {
                if (line.startsWith("- " + name)) {
                    in = true;
                    value.append(line.substring(line.indexOf(':') + 1)).append('\n');
                } else if (in && line.matches("^- [А-ЯA-Z][^:]{0,60}:.*")) {
                    break;
                } else if (in) {
                    value.append(line).append('\n');
                }
            }
            return value.toString().trim();
        }

        static Map<String, String> fileTable(String body) {
            Map<String, String> files = new LinkedHashMap<>();
            for (String line : body.split("\n")) {
                String[] cells = cells(line);
                if (cells.length >= 3 && cells[2].matches(".*(изменить|создать|удалить|добавлен|удалён).*")) {
                    String path = cells[0].replace("`", "").trim();
                    if (!path.isEmpty() && !path.startsWith("<") && !path.startsWith("Файл")) {
                        files.put(path, cells[2]);
                    }
                }
            }
            return files;
        }

        static String[] cells(String line) {
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
    }
}
