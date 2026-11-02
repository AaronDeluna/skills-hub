import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;

/**
 * Ключи тест-кейсов (<КОД>-T<цифры>) в тест-методах - для разметки (markup-rules.md, разделы 2а и 6).
 *
 * java -Dfile.encoding=UTF-8 MarkupKeys.java missing <каталог тестов>...  - ключ есть, @TmsLink нет
 * java -Dfile.encoding=UTF-8 MarkupKeys.java dup <каталог тестов>...      - один ключ у разных тест-методов
 *
 * Ключ метода - из его @DisplayName, а если там нет - из name его @ParameterizedTest.
 * Для dup считаются все ключи метода: из @DisplayName, из name и из @TmsLink. @DisplayName над классом не считается.
 * Аннотации могут быть многострочными и стоять на одной строке с объявлением.
 */
public class MarkupKeys {

    private static final Pattern KEY = Pattern.compile("[A-Z][A-Z0-9]*-T[0-9]+");
    private static final Pattern STRING = Pattern.compile("\"(?:[^\"\\\\]|\\\\.)*\"");
    private static final Pattern ANNOTATION = Pattern.compile("@[A-Za-z_.]+(\\([^)]*\\))?");
    private static final Pattern CLASS = Pattern.compile("(^|\\s)(class|interface|object|enum)\\s");
    private static final Pattern METHOD_ON_LINE = Pattern.compile("(void|fun)\\s+[A-Za-z_]");
    private static final Pattern NAME = Pattern.compile("[A-Za-z_][A-Za-z0-9_]*\\s*\\(");

    private record Method(String place, String name, Set<String> keys, Set<String> all, boolean hasLink) {
    }

    public static void main(String[] args) throws IOException {
        System.setOut(new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8));
        if (args.length < 2 || !(args[0].equals("missing") || args[0].equals("dup"))) {
            System.out.println("использование: MarkupKeys.java missing|dup <каталог тестов>...");
            System.exit(2);
        }
        List<Method> methods = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            List<Path> files;
            try (Stream<Path> walk = Files.walk(Paths.get(args[i]))) {
                files = walk.filter(p -> p.toString().endsWith(".java") || p.toString().endsWith(".kt"))
                        .filter(p -> !p.toString().contains("/target/") && !p.toString().contains("/build/"))
                        .sorted().toList();
            }
            for (Path file : files) {
                methods.addAll(parse(file));
            }
        }
        int found = 0;
        if (args[0].equals("missing")) {
            for (Method m : methods) {
                if (!m.keys().isEmpty() && !m.hasLink()) {
                    System.out.println(m.place() + ": " + m.name() + " - " + String.join(" ", m.keys()) + " - нет @TmsLink");
                    found++;
                }
            }
        } else {
            Map<String, List<String>> byKey = new TreeMap<>();
            for (Method m : methods) {
                for (String key : m.all()) {
                    byKey.computeIfAbsent(key, k -> new ArrayList<>()).add(m.place() + ":" + m.name());
                }
            }
            for (Map.Entry<String, List<String>> e : byKey.entrySet()) {
                if (e.getValue().size() > 1) {
                    System.out.println(e.getKey() + " - " + String.join(" ", e.getValue()));
                    found++;
                }
            }
        }
        System.out.println("итого: " + found);
    }

    private static List<Method> parse(Path file) throws IOException {
        List<Method> result = new ArrayList<>();
        List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
        State st = new State();
        for (int n = 0; n < lines.size(); n++) {
            String line = lines.get(n);
            String place = file + ":" + (n + 1);
            if (st.depth > 0 || st.textBlock) {
                if (st.open == 'd') {
                    addKeys(st.displayKeys, line);
                } else if (st.open == 'p') {
                    addKeys(st.nameKeys, line);
                }
                st.update(line);
                if (st.depth <= 0 && !st.textBlock) {
                    st.open = ' ';
                }
                continue;
            }
            String trimmed = line.strip();
            if (trimmed.startsWith("@")) {
                if (line.contains("@TmsLink(")) {
                    st.hasLink = true;
                    addKeys(st.linkKeys, line.substring(line.indexOf("@TmsLink(")));
                }
                if (line.contains("@DisplayName(")) {
                    st.display = true;
                    addKeys(st.displayKeys, line.substring(line.indexOf("@DisplayName(")));
                }
                if (line.contains("@ParameterizedTest(")) {
                    addKeys(st.nameKeys, line.substring(line.indexOf("@ParameterizedTest(")));
                }
                st.depth = 0;
                st.update(line);
                if (st.depth > 0) {
                    if (line.matches(".*@DisplayName\\([^)]*$")) {
                        st.open = 'd';
                    } else if (line.matches(".*@ParameterizedTest\\([^)]*$")) {
                        st.open = 'p';
                    }
                }
                String code = STRING.matcher(line).replaceAll("");
                if (CLASS.matcher(code).find()) {
                    st.reset();
                } else if (st.depth <= 0 && !st.textBlock && METHOD_ON_LINE.matcher(code).find()) {
                    declaration(st, line, place, result);
                }
                continue;
            }
            if (trimmed.isEmpty() || trimmed.startsWith("//") || trimmed.startsWith("/*") || trimmed.startsWith("*")) {
                continue;
            }
            if (CLASS.matcher(STRING.matcher(line).replaceAll("")).find()) {
                st.reset();
            } else {
                declaration(st, line, place, result);
            }
        }
        return result;
    }

    private static void declaration(State st, String line, String place, List<Method> result) {
        Set<String> keys = st.display ? st.displayKeys : st.nameKeys;
        Set<String> all = new LinkedHashSet<>(st.displayKeys);
        all.addAll(st.nameKeys);
        all.addAll(st.linkKeys);
        if (!all.isEmpty()) {
            String code = ANNOTATION.matcher(STRING.matcher(line).replaceAll("")).replaceAll("");
            Matcher m = NAME.matcher(code);
            String name = m.find() ? m.group().replaceAll("\\s*\\($", "") : "?";
            result.add(new Method(place, name, new LinkedHashSet<>(keys), all, st.hasLink));
        }
        st.reset();
    }

    private static void addKeys(Set<String> target, String text) {
        Matcher m = KEY.matcher(text);
        while (m.find()) {
            target.add(m.group());
        }
    }

    private static final class State {
        boolean hasLink;
        boolean display;
        boolean textBlock;
        int depth;
        char open = ' ';
        Set<String> displayKeys = new LinkedHashSet<>();
        Set<String> nameKeys = new LinkedHashSet<>();
        Set<String> linkKeys = new LinkedHashSet<>();

        void reset() {
            hasLink = false;
            display = false;
            open = ' ';
            displayKeys = new LinkedHashSet<>();
            nameKeys = new LinkedHashSet<>();
            linkKeys = new LinkedHashSet<>();
        }

        void update(String s) {
            if (textBlock) {
                int i = s.indexOf("\"\"\"");
                if (i < 0) {
                    return;
                }
                textBlock = false;
                s = s.substring(i + 3);
            }
            int i = s.indexOf("\"\"\"");
            if (i >= 0) {
                textBlock = true;
                s = s.substring(0, i);
            }
            s = STRING.matcher(s).replaceAll("");
            for (char c : s.toCharArray()) {
                if (c == '(') {
                    depth++;
                } else if (c == ')') {
                    depth--;
                }
            }
        }
    }
}
