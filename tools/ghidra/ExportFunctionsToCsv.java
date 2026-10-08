// Export the functions you've named in Ghidra to fe3h-decomp's functions.csv.
// New functions are added with status "todo". Existing rows get their name and
// size updated; their status, file and notes are never touched.
//@category fe3h-decomp

import java.io.File;
import java.nio.file.Files;
import java.util.List;
import java.util.TreeMap;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

public class ExportFunctionsToCsv extends GhidraScript {

    @Override
    public void run() throws Exception {
        File csv = askFile("Select functions.csv", "Export");
        String text = Files.readString(csv.toPath());
        String newline = text.contains("\r\n") ? "\r\n" : "\n";
        List<String> lines = text.lines().toList();

        // address -> {address, size, name, status, file, notes}
        TreeMap<Long, String[]> rows = new TreeMap<>();
        for (String line : lines.subList(1, lines.size())) {
            if (line.isBlank()) {
                continue;
            }
            String[] cols = line.split(",", 6);
            rows.put(Long.decode(cols[0]), cols);
        }

        int added = 0, updated = 0;
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            if (f.isThunk() || f.isExternal()) {
                continue;
            }
            if (f.getSymbol().getSource() != SourceType.USER_DEFINED) {
                continue;   // only functions you named yourself
            }
            long address = f.getEntryPoint().getOffset();
            // Only the block starting at the entry point: Ghidra can attach
            // extra pieces (like an import stub the function jumps to).
            long length = f.getBody().getRangeContaining(f.getEntryPoint()).getLength();
            String size = String.format("0x%X", length);
            String name = f.getName(true);   // includes the class, e.g. Camera::Set

            String[] row = rows.get(address);
            if (row == null) {
                rows.put(address, new String[] { String.format("0x%X", address), size, name, "todo", "", "" });
                added++;
            }
            else if (!row[1].equalsIgnoreCase(size) || !row[2].equals(name)) {
                println("updated " + row[2] + " -> " + name + " (" + size + ")");
                row[1] = size;
                row[2] = name;
                updated++;
            }
        }

        StringBuilder out = new StringBuilder(lines.get(0)).append(newline);
        for (String[] row : rows.values()) {
            out.append(String.join(",", row)).append(newline);
        }
        Files.writeString(csv.toPath(), out.toString());
        println("functions.csv: " + added + " added, " + updated + " updated, " + rows.size() + " total");
    }
}
