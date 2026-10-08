// Apply fe3h-decomp's functions.csv to this program: creates any missing
// functions, names them (with their class), and tags each with its decomp
// status (decomp:matching, decomp:wip, ...). Safe to run again after updates.
//@category fe3h-decomp

import java.io.File;
import java.nio.file.Files;
import java.util.List;

import ghidra.app.script.GhidraScript;
import ghidra.app.util.NamespaceUtils;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionTag;
import ghidra.program.model.symbol.Namespace;
import ghidra.program.model.symbol.SourceType;

public class ImportFunctionsFromCsv extends GhidraScript {

    private static final String TAG_PREFIX = "decomp:";

    @Override
    public void run() throws Exception {
        File csv = askFile("Select functions.csv", "Import");
        List<String> lines = Files.readString(csv.toPath()).lines().toList();

        int named = 0, created = 0;
        for (String line : lines.subList(1, lines.size())) {
            if (line.isBlank()) {
                continue;
            }
            String[] cols = line.split(",", 6);
            Address address = toAddr(Long.decode(cols[0]));
            String name = cols[2];
            String status = cols[3];

            Function f = getFunctionAt(address);
            if (f == null) {
                disassemble(address);   // in case Ghidra hasn't analyzed this code yet
                f = createFunction(address, null);
                if (f == null) {
                    printerr("Couldn't create a function at " + address);
                    continue;
                }
                created++;
            }

            if (!name.isEmpty()) {
                int split = name.lastIndexOf("::");   // Camera::Set -> class "Camera", name "Set"
                Namespace ns = currentProgram.getGlobalNamespace();
                String shortName = name;
                if (split >= 0) {
                    ns = NamespaceUtils.createNamespaceHierarchy(name.substring(0, split), null,
                        currentProgram, SourceType.USER_DEFINED);
                    shortName = name.substring(split + 2);
                }
                f.setParentNamespace(ns);
                f.setName(shortName, SourceType.USER_DEFINED);
                named++;
            }

            for (FunctionTag tag : List.copyOf(f.getTags())) {
                if (tag.getName().startsWith(TAG_PREFIX)) {
                    f.removeTag(tag.getName());
                }
            }
            f.addTag(TAG_PREFIX + status);
        }
        println("Imported " + named + " names, created " + created + " functions");
    }
}
