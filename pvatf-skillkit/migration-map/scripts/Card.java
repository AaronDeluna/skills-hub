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
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Механическая проверка карточек юнитов (скилл migration-map). Запуск из корня проекта:
 *
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Card.java M-007   - одна карточка
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Card.java all     - все карточки todo
 *
 * Проверяет то, что можно проверить без модели: поля подшагов, пустые слова, лимиты,
 * покрытие потребителей, legacy, записи конспекта, «создал - подключи», число строк.
 * Смысл шагов не проверяет - это работа сабагента «проверяющий карточки».
 * Код выхода 0 - чисто, 1 - есть находки.
 */
public class Card {

    private static final Path MIGRATION = Paths.get(".gigacode", "data", "migration");
    private static final Pattern EMPTY_WORDS = Pattern.compile(
            "(?iu)\\b(мигрировать|адаптировать|привести в порядок|при необходимости|и так далее|соответствующ\\S*|доработать)\\b");
    private static final Map<String, Integer> LIMITS = Map.of("env", 6, "core", 6, "usage", 3, "cleanup", 15, "review", 15);

    private static final List<String> problems = new ArrayList<>();

    public static void main(String[] args) throws IOException {
        System.setOut(new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8));
        if (args.length == 0) {
            System.out.println("Использование: java Card.java <M-nnn | all>");
            System.exit(2);
        }
        String map = read(MIGRATION.resolve("MIGRATION-MAP.md"));
        List<Path> cards = new ArrayList<>();
        if (args[0].equals("all")) {
            if (!Files.isDirectory(MIGRATION.resolve("units"))) {
                System.out.println("Карточек нет: папки " + MIGRATION.resolve("units") + " нет. Запускай из корня проекта, где лежит .gigacode/");
                System.exit(1);
            }
            try (Stream<Path> files = Files.list(MIGRATION.resolve("units"))) {
                files.filter(p -> p.getFileName().toString().matches("M-[0-9]+\\.md")).sorted().forEach(cards::add);
            }
        } else {
            cards.add(MIGRATION.resolve("units").resolve(args[0] + ".md"));
        }
        int total = 0;
        for (Path path : cards) {
            String text = read(path);
            if (text.isEmpty()) {
                System.out.println(path + ": карточки нет");
                total++;
                continue;
            }
            if (args[0].equals("all") && !front(text, "status").equals("todo")) {
                continue;
            }
            problems.clear();
            if (front(text, "type").equals("tech")) {
                checkTech(text, map);
            } else {
                checkPlain(text);
            }
            checkDocRefs(text, front(text, "tech"));
            String id = front(text, "id");
            System.out.println(id + ": " + (problems.isEmpty() ? "чисто" : "находок " + problems.size()));
            for (String problem : problems) {
                System.out.println("  - " + problem);
            }
            total += problems.size();
        }
        System.out.println("ИТОГ: находок " + total);
        System.exit(total == 0 ? 0 : 1);
    }

    // ---------- tech ----------

    private static void checkTech(String text, String map) {
        Map<String, String> sections = sections(text);
        List<String[]> steps = new ArrayList<>();
        for (String line : sections.getOrDefault("Подшаги", "").split("\n")) {
            String[] cells = cells(line);
            if (cells.length >= 5 && cells[0].matches("S-[0-9]+")) {
                steps.add(cells);
            }
        }
        if (steps.isEmpty()) {
            problems.add("нет таблицы «Подшаги»");
            return;
        }
        Map<String, String> bodies = new LinkedHashMap<>();
        Map<String, Map<String, String>> files = new LinkedHashMap<>();
        for (String[] step : steps) {
            String id = step[0];
            String kind = step[1];
            String body = null;
            for (Map.Entry<String, String> section : sections.entrySet()) {
                if (section.getKey().startsWith(id + " ")) {
                    body = section.getValue();
                }
            }
            if (body == null) {
                problems.add(id + ": нет раздела «## " + id + " · ...»");
                continue;
            }
            bodies.put(id, body);
            files.put(id, fileTable(body));
            checkTitle(id, step[2]);
            if (kind.equals("разбор") || kind.equals("review")) {
                continue;
            }
            checkStep(id, kind, body, files.get(id));
        }
        checkConsumers(sections.getOrDefault("Разбор технологии", ""), steps, files);
        checkCreatedAreUsed(steps, files, bodies, front(text, "tech"));
        checkLegacy(text, map, front(text, "tech"));
    }

    private static void checkTitle(String id, String title) {
        Matcher empty = EMPTY_WORDS.matcher(title);
        if (empty.find()) {
            problems.add(id + ": в названии слово без содержания «" + empty.group() + "» - напиши, что станет, с именами");
        }
    }

    private static void checkStep(String id, String kind, String body, Map<String, String> stepFiles) {
        if (stepFiles.isEmpty()) {
            problems.add(id + ": нет таблицы файлов (Файл | Строк | Действие)");
        }
        Integer limit = LIMITS.get(kind);
        if (limit != null && stepFiles.size() > limit) {
            problems.add(id + ": файлов " + stepFiles.size() + " при лимите " + limit + " для " + kind + " - раздели подшаг");
        }
        String todo = field(body, "Что сделать");
        if (!todo.matches("(?s).*\\b1\\..*")) {
            problems.add(id + ": «Что сделать» без пронумерованных действий");
        }
        Matcher empty = EMPTY_WORDS.matcher(todo + " " + field(body, "Итоговый результат"));
        while (empty.find()) {
            problems.add(id + ": слово без содержания «" + empty.group() + "» - замени конкретным действием с именами");
        }
        if (field(body, "Итоговый результат").length() < 10) {
            problems.add(id + ": пустой «Итоговый результат»");
        }
        String checkpoint = field(body, "Чекпоинт");
        if (!checkpoint.contains("`") || !checkpoint.contains("->")) {
            problems.add(id + ": «Чекпоинт» должен быть одной командой в `...` и ожидаемым выводом после ->");
        }
        if (kind.equals("usage") || kind.equals("fix")) {
            Map<String, String> criteria = new LinkedHashMap<>();
            String table = field(body, "Критерии по файлам");
            for (String line : table.split("\n")) {
                String[] cells = cells(line);
                if (cells.length >= 4 && !cells[0].equals("Файл") && !cells[0].startsWith("-") && !cells[0].startsWith("<")) {
                    criteria.put(cells[0].replace("`", ""), cells[1]);
                }
            }
            for (Map.Entry<String, String> file : stepFiles.entrySet()) {
                if (!file.getValue().contains("изменить")) {
                    continue;
                }
                String was = criteria.get(file.getKey());
                if (was == null) {
                    problems.add(id + ": нет строки «Критерии по файлам» для " + file.getKey());
                } else if (!was.matches(".*[0-9].*")) {
                    problems.add(id + ": в «Было» для " + file.getKey() + " нет чисел из разбора");
                }
            }
        }
        if ((kind.equals("usage") || kind.equals("fix")) && !checkpoint.matches("(?s).*(assert|Matcher|JsonNode).*")) {
            problems.add(id + ": в «Чекпоинте» usage/fix нет команды MR-48 (ассерты, свои matchers, JsonNode)");
        }
        String rules = field(body, "Правила подшага");
        int count = 0;
        Matcher rule = Pattern.compile("MR-[0-9H]+").matcher(rules);
        while (rule.find()) {
            count++;
        }
        if (count == 0) {
            problems.add(id + ": пустое поле «Правила подшага»");
        } else if (count > 10) {
            problems.add(id + ": правил " + count + ", больше 10 не бывает");
        }
        for (Map.Entry<String, String> file : stepFiles.entrySet()) {
            Path path = Paths.get(file.getKey());
            if (file.getValue().contains("создать")) {
                if (Files.exists(path)) {
                    problems.add(id + ": " + file.getKey() + " помечен «создать», но уже есть");
                }
                continue;
            }
            if (!Files.exists(path)) {
                problems.add(id + ": " + file.getKey() + " - файла нет в проекте");
                continue;
            }
            int declared = parseInt(lineCount(body, file.getKey()));
            try {
                long real = Files.lines(path, StandardCharsets.UTF_8).count();
                if (declared > 0 && Math.abs(real - declared) > Math.max(10, real / 5)) {
                    problems.add(id + ": " + file.getKey() + " - в карточке " + declared + " строк, в файле " + real);
                }
            } catch (IOException | java.io.UncheckedIOException e) {
                problems.add(id + ": " + file.getKey() + " - не читается");
            }
        }
    }

    /** Каждый потребитель - ровно в одном usage, и в колонке «Подшаг» стоит этот usage. */
    private static void checkConsumers(String analysis, List<String[]> steps, Map<String, Map<String, String>> files) {
        for (String line : analysis.split("\n")) {
            String[] cells = cells(line);
            if (cells.length < 6 || cells[0].startsWith("Потребитель") || cells[0].startsWith("-") || cells[0].startsWith("<")) {
                continue;
            }
            String consumer = cells[0].replace("`", "");
            String declared = cells[cells.length - 1];
            if (declared.contains("уже нет")) {
                continue;
            }
            List<String> in = new ArrayList<>();
            for (String[] step : steps) {
                if (step[1].equals("usage") && files.getOrDefault(step[0], Map.of()).containsKey(consumer)) {
                    in.add(step[0]);
                }
            }
            if (in.isEmpty()) {
                problems.add("потребитель " + consumer + " не стоит ни в одном подшаге usage");
            } else if (in.size() > 1) {
                problems.add("потребитель " + consumer + " стоит в нескольких usage: " + String.join(", ", in));
            } else if (!declared.contains(in.get(0))) {
                problems.add("потребитель " + consumer + ": в колонке «Подшаг» " + declared + ", а в таблице файлов - " + in.get(0));
            }
        }
    }

    /** Создал - подключи: класс из core упоминается в каком-нибудь usage. */
    private static void checkCreatedAreUsed(List<String[]> steps, Map<String, Map<String, String>> files,
                                            Map<String, String> bodies, String tech) {
        StringBuilder usage = new StringBuilder();
        for (String[] step : steps) {
            if (step[1].equals("usage")) {
                usage.append(bodies.getOrDefault(step[0], ""));
            }
        }
        boolean hasUsage = steps.stream().anyMatch(s -> s[1].equals("usage"));
        for (String[] step : steps) {
            if (!step[1].equals("core")) {
                continue;
            }
            for (Map.Entry<String, String> file : files.getOrDefault(step[0], Map.of()).entrySet()) {
                if (!file.getValue().contains("создать")) {
                    continue;
                }
                String name = Paths.get(file.getKey()).getFileName().toString().replaceAll("\\.(java|kt)$", "");
                boolean baseLayer = name.equalsIgnoreCase(tech.replace("-", "") + "Steps");
                boolean otherStep = false;
                for (Map.Entry<String, String> other : bodies.entrySet()) {
                    if (!other.getKey().equals(step[0]) && other.getValue().contains(name)) {
                        otherStep = true;
                    }
                }
                if (hasUsage && !baseLayer && !otherStep && !usage.toString().contains(name)
                        && !name.startsWith("Base") && !name.endsWith("Configuration")) {
                    problems.add(step[0] + ": создаётся " + name + ", но ни один подшаг usage на него не переводит (создал - подключи)");
                }
            }
        }
    }

    /** Строки L этой технологии из карты упомянуты в карточке. */
    private static void checkLegacy(String text, String map, String tech) {
        for (String line : map.split("\n")) {
            String[] cells = cells(line);
            if (cells.length >= 3 && cells[0].matches("L-[0-9]+") && cells[1].equals(tech)) {
                String body = text.replaceFirst("(?s)^---.*?\n---\n", "");
                if (!Pattern.compile("\\b" + cells[0] + "\\b").matcher(body).find()) {
                    problems.add(cells[0] + " (" + cells[2] + ") технологии " + tech + " не удаляется ни в одном подшаге");
                }
            }
        }
    }

    // ---------- обычный юнит ----------

    private static void checkPlain(String text) {
        Map<String, String> sections = sections(text);
        if (fileTable(sections.getOrDefault("Файлы юнита", "")).isEmpty()) {
            problems.add("нет таблицы «Файлы юнита»");
        }
        String todo = sections.getOrDefault("Что сделать", "");
        if (!todo.matches("(?s).*\\b1\\..*")) {
            problems.add("«Что сделать» без пронумерованных действий");
        }
        Matcher empty = EMPTY_WORDS.matcher(todo);
        while (empty.find()) {
            problems.add("слово без содержания «" + empty.group() + "» в «Что сделать»");
        }
        if (!sections.getOrDefault("Правила юнита", "").matches("(?s).*MR-[0-9H]+.*")) {
            problems.add("пустой раздел «Правила юнита»");
        }
        if (sections.getOrDefault("Критерии готовности", "").contains("<точный grep")) {
            problems.add("в «Критериях готовности» не подставлен grep-шаблон");
        }
    }

    /** Каждая ссылка D-<tech>-n есть в конспекте. */
    private static void checkDocRefs(String text, String tech) {
        Matcher ref = Pattern.compile("\\bD-([a-z0-9-]+?)-([0-9]+)\\b").matcher(text);
        Map<String, String> notes = new LinkedHashMap<>();
        java.util.Set<String> seen = new java.util.HashSet<>();
        while (ref.find()) {
            if (!seen.add(ref.group())) {
                continue;
            }
            String noteTech = ref.group(1);
            String notesText = notes.computeIfAbsent(noteTech, t -> read(MIGRATION.resolve("doc-notes").resolve(t + ".md")));
            if (!notesText.contains(ref.group())) {
                problems.add("ссылка " + ref.group() + " - такой записи нет в doc-notes/" + noteTech + ".md");
            }
        }
    }

    // ---------- разбор markdown ----------

    private static String lineCount(String body, String path) {
        for (String line : body.split("\n")) {
            String[] cells = cells(line);
            if (cells.length >= 3 && cells[0].replace("`", "").equals(path)) {
                return cells[1].replaceAll("[^0-9]", "");
            }
        }
        return "0";
    }

    private static Map<String, String> fileTable(String body) {
        Map<String, String> files = new LinkedHashMap<>();
        for (String line : body.split("\n")) {
            String[] cells = cells(line);
            if (cells.length >= 3 && cells[2].matches(".*(изменить|создать|удалить).*")) {
                String path = cells[0].replace("`", "").trim();
                if (!path.isEmpty() && !path.startsWith("<")) {
                    files.put(path, cells[2]);
                }
            }
        }
        return files;
    }

    private static String field(String body, String name) {
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

    private static Map<String, String> sections(String text) {
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

    private static String front(String text, String key) {
        Matcher m = Pattern.compile("(?m)^" + key + ":\\s*(.*)$").matcher(text);
        return m.find() ? m.group(1).trim() : "-";
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

    private static String read(Path path) {
        try {
            return Files.exists(path) ? Files.readString(path, StandardCharsets.UTF_8) : "";
        } catch (IOException e) {
            return "";
        }
    }
}
