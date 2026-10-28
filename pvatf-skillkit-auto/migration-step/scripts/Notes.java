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
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Поиск по конспекту документации (doc-notes/). Запуск из корня проекта:
 *
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Notes.java list <tech>             - оглавление: ID, статус, вопрос
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Notes.java find <tech> <слова...>  - записи, где есть эти слова
 *   java -Dfile.encoding=UTF-8 <каталог скилла>/scripts/Notes.java show D-rest-3 D-rest-5  - записи целиком
 *
 * find и list смотрят конспект технологии и общий (common). Слово ищется без учёта регистра
 * и по началу слова (matcher найдёт matchers). Ничего не меняет.
 */
public class Notes {

    private static final Path NOTES = Paths.get(".gigacode", "data", "migration", "doc-notes");

    public static void main(String[] args) throws IOException {
        System.setOut(new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8));
        if (args.length < 2) {
            System.out.println("Использование: Notes.java list <tech> | find <tech> <слова...> | show <D-id...>");
            System.exit(2);
        }
        String command = args[0];
        if (command.equals("show")) {
            for (String id : Arrays.copyOfRange(args, 1, args.length)) {
                Record record = byId(id);
                System.out.println(record == null ? id + ": такой записи в конспекте нет" : record.text.trim());
                System.out.println();
            }
            return;
        }
        List<Record> records = records(args[1]);
        if (command.equals("list")) {
            if (records.isEmpty()) {
                System.out.println("Конспекта по " + args[1] + " и common пока нет.");
            }
            for (Record record : records) {
                System.out.println(record.id + " · " + record.status + " · " + record.question);
            }
            return;
        }
        if (command.equals("find")) {
            List<String> words = new ArrayList<>();
            for (String word : Arrays.copyOfRange(args, 2, args.length)) {
                String clean = word.toLowerCase(Locale.ROOT).replaceAll("[^\\p{L}\\p{N}_.]", "");
                if (clean.length() >= 3) {
                    words.add(clean.length() > 6 ? clean.substring(0, clean.length() - 2) : clean);
                }
            }
            List<Record> found = new ArrayList<>();
            for (Record record : records) {
                String lower = record.text.toLowerCase(Locale.ROOT);
                record.score = (int) words.stream().filter(lower::contains).count();
                if (record.score > 0) {
                    found.add(record);
                }
            }
            found.sort(Comparator.comparingInt((Record r) -> -r.score));
            if (found.isEmpty()) {
                System.out.println("В конспекте ничего по словам: " + String.join(", ", words)
                        + ". Попробуй другие слова (имя класса фрейма, раздел документации); не нашлось - сабагент документации.");
                return;
            }
            System.out.println("Нашлось записей: " + found.size() + " (сначала лучшие совпадения). Полностью: Notes.java show <ID>");
            for (Record record : found.subList(0, Math.min(8, found.size()))) {
                System.out.println();
                System.out.println(record.id + " · " + record.status + " · совпало слов " + record.score + "/" + words.size());
                System.out.println("  вопрос: " + record.question);
                System.out.println("  что использовать: " + shorten(record.field("Что использовать")));
                String phrases = record.field("Формулировки запросов");
                if (!record.status.equals("найден") && !phrases.isEmpty()) {
                    System.out.println("  уже спрашивали так: " + shorten(phrases));
                }
            }
            return;
        }
        System.out.println("Неизвестная команда: " + command);
        System.exit(2);
    }

    static final class Record {
        String id;
        String question;
        String status = "-";
        String text;
        int score;

        String field(String name) {
            for (String line : text.split("\n")) {
                if (line.startsWith("- " + name)) {
                    return line.substring(line.indexOf(':') + 1).trim();
                }
            }
            return "";
        }
    }

    private static List<Record> records(String tech) throws IOException {
        List<Record> all = new ArrayList<>();
        all.addAll(parse(NOTES.resolve(tech + ".md")));
        if (!tech.equals("common")) {
            all.addAll(parse(NOTES.resolve("common.md")));
        }
        return all;
    }

    private static Record byId(String id) throws IOException {
        if (!Files.isDirectory(NOTES)) {
            return null;
        }
        try (Stream<Path> files = Files.list(NOTES)) {
            for (Path file : files.collect(Collectors.toList())) {
                for (Record record : parse(file)) {
                    if (record.id.equals(id)) {
                        return record;
                    }
                }
            }
        }
        return null;
    }

    private static List<Record> parse(Path file) throws IOException {
        List<Record> records = new ArrayList<>();
        if (!Files.exists(file)) {
            return records;
        }
        Record current = null;
        StringBuilder body = new StringBuilder();
        for (String line : Files.readString(file, StandardCharsets.UTF_8).split("\n", -1)) {
            if (line.matches("^#{2,3} D-[A-Za-z0-9-]+-[0-9]+\\b.*")) {
                if (current != null) {
                    current.text = body.toString();
                    records.add(current);
                }
                current = new Record();
                String head = line.replaceFirst("^#+\\s*", "");
                current.id = head.split("\\s")[0];
                int dot = head.indexOf('·');
                current.question = dot >= 0 ? head.substring(dot + 1).trim() : head;
                body.setLength(0);
            }
            if (current != null) {
                body.append(line).append('\n');
                if (line.startsWith("- Статус:")) {
                    current.status = line.substring(line.indexOf(':') + 1).trim();
                }
            }
        }
        if (current != null) {
            current.text = body.toString();
            records.add(current);
        }
        return records;
    }

    private static String shorten(String text) {
        String compact = text.replaceAll("\\s+", " ").trim();
        return compact.length() > 220 ? compact.substring(0, 220) + "..." : (compact.isEmpty() ? "-" : compact);
    }
}
