import java.io.File;
import java.util.prefs.Preferences;

/**
 * Works around an SPMF v2.66 GUI bug: on the first use, the "choose input/output file"
 * dialog looks up a class file that is missing from spmf.jar and crashes with a
 * NullPointerException. Saving a starting folder in SPMF's preferences skips that lookup.
 *
 * <p>Run from the {@code tools/spmf} folder: {@code java FixSpmfGuiPaths.java}
 */
public class FixSpmfGuiPaths {

    /**
     * Stores the project's {@code data} folder as SPMF's last input and output folder.
     *
     * @param args unused
     * @throws Exception if the preferences cannot be written
     */
    public static void main(String[] args) throws Exception {
        String dataDir = new File("../../data").getCanonicalPath();
        Preferences prefs = Preferences.userRoot();
        prefs.put("ca.pfv.spmf.gui.input", dataDir);
        prefs.put("ca.pfv.spmf.gui.output", dataDir);
        prefs.flush();
        System.out.println("SPMF input/output folder set to: " + dataDir);
    }
}
