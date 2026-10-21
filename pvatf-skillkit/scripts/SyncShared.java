import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.util.Map;

/**
 * Для разработчиков кита. Общие файлы лежат в shared/ - это источник. Скиллы ставятся
 * по отдельности, поэтому каждому нужна своя копия в references/. Запуск из папки кита:
 *
 *   java -Dfile.encoding=UTF-8 scripts/SyncShared.java          - разложить копии
 *   java -Dfile.encoding=UTF-8 scripts/SyncShared.java --check  - проверить, что копии совпадают (код выхода 1 - нет)
 */
public class SyncShared {

    private static final Map<String, List<String>> COPIES = Map.of(
            "core-rules.md", List.of("orchestrator", "migration-map", "migration-step", "migration-review"),
            "matchers.md", List.of("migration-map", "migration-step"),
            "frame-topics.md", List.of("migration-map", "migration-step"),
            "architecture-template.md", List.of("migration-map", "migration-review"));

    public static void main(String[] args) throws IOException {
        System.setOut(new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8));
        boolean check = args.length > 0 && args[0].equals("--check");
        int differ = 0;
        for (Map.Entry<String, List<String>> entry : COPIES.entrySet()) {
            Path source = Paths.get("shared", entry.getKey());
            byte[] content = Files.readAllBytes(source);
            for (String skill : entry.getValue()) {
                Path target = Paths.get(skill, "references", entry.getKey());
                boolean same = Files.exists(target) && java.util.Arrays.equals(content, Files.readAllBytes(target));
                if (same) {
                    continue;
                }
                if (check) {
                    System.out.println("РАЗОШЛОСЬ: " + target + " не совпадает с " + source);
                    differ++;
                } else {
                    Files.createDirectories(target.getParent());
                    Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
                    System.out.println("обновлено: " + target);
                }
            }
        }
        System.out.println(check ? (differ == 0 ? "все копии совпадают" : "разошлось копий: " + differ) : "готово");
        System.exit(differ == 0 ? 0 : 1);
    }
}
