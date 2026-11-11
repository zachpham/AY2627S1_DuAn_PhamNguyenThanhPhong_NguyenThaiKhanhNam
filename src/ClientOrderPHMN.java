import java.io.IOException;
import java.lang.reflect.Field;
import java.net.URISyntaxException;
import java.nio.file.Paths;
import java.security.CodeSource;

import ca.pfv.spmf.algorithms.frequentpatterns.phmn_plus.AlgoPHMN;

/**
 * Experiment E8 for the PHMN algorithm: does the order in which the two co-occurrence filters
 * EUCP and ESCP are applied change the result or the cost?
 *
 * <p>The server class is {@code AlgoPHMN}. E8 compares three variants of it, generated from the
 * corrected build by {@code tools/sinh_e8.py} and compiled into separate folders:</p>
 *
 * <ul>
 *   <li>{@code build/e8_a}: EUCP first, then ESCP, the order of the implementation;</li>
 *   <li>{@code build/e8_b}: ESCP first, then EUCP;</li>
 *   <li>{@code build/e8_c}: the order of {@code e8_a}, with the two map lookups that do not depend
 *       on the inner loop moved out of it.</li>
 * </ul>
 *
 * <p>All three variants share the class name {@code AlgoPHMN} in the same package, so one JVM
 * can hold only one of them. The variant is therefore chosen by the class path: the folder of
 * the variant is placed before {@code spmf.jar}, and the JVM loads the variant in preference to
 * the class inside the jar. This client prints the folder the class was actually loaded from, so
 * a wrong class path is visible in the log instead of silently measuring the wrong build.</p>
 *
 * <p>Each variant counts how many candidate pairs reach the filters and how many each filter
 * rejects. Since every pair is either rejected by one of the two filters or becomes a candidate,
 * the counts must satisfy {@code pairsConsidered = rejEUCP + rejESCP + candidateCount}. The
 * client checks this and exits with status 1 if it fails.</p>
 *
 * <p>The client runs the algorithm exactly as {@code ca.pfv.spmf.gui.Main run PHMN} does:
 * plain PHMN (not PHMN+), the same five integer thresholds, then the statistics of the
 * algorithm. Its output therefore contains every line that {@code tools/chay_e8.ps1} reads.</p>
 *
 * <p>How to run, from the project root directory:</p>
 *
 * <pre>
 * javac -cp tools/spmf/spmf.jar -d build/clients src/ClientOrderPHMN.java
 * java -Xmx6g -cp "build/e8_a;tools/spmf/spmf.jar;build/clients" ClientOrderPHMN &lt;input&gt; &lt;output&gt; &lt;minUtil&gt; &lt;minPer&gt; &lt;maxPer&gt; &lt;minAvg&gt; &lt;maxAvg&gt;
 *
 * java -Xmx6g -cp "build/e8_b;tools/spmf/spmf.jar;build/clients" ClientOrderPHMN data/mushroom_negative.txt output/e8.txt 100000 1 3000 1 2000
 * </pre>
 *
 * <p>The client is compiled once rather than run as a source file, so that compiling it is not
 * counted in the CPU time that E8 measures. It reads the counters by reflection, so it compiles
 * against {@code spmf.jar} alone. Always pass relative paths: a path containing Vietnamese
 * characters can reach the JVM corrupted on Windows.</p>
 */
public class ClientOrderPHMN
{
    /** Number of command line arguments the client expects. */
    private static final int EXPECTED_ARGUMENT_COUNT = 7;

    /** Exit status when the counting invariant fails. */
    private static final int EXIT_INVARIANT_FAILED = 1;

    /** Exit status when the arguments are wrong or the loaded class is not an E8 variant. */
    private static final int EXIT_USAGE = 2;

    /** Names of the public counter fields that every E8 variant adds to AlgoPHMN. */
    private static final String[] COUNTER_NAMES =
    {
        "candidateCount", "pairsConsidered", "rejEUCP", "rejESCP",
        "constructNull", "rejLAutil", "rejLAsup"
    };

    /**
     * Not used: the client is run through {@link #main(String[])} and holds no state.
     */
    private ClientOrderPHMN()
    {
    }

    /**
     * Runs one E8 measurement and prints the counters on one line.
     *
     * @param args input file, output file, minUtil, minPer, maxPer, minAvg and maxAvg
     * @throws IOException if the input cannot be read or the output cannot be written
     */
    public static void main(String[] args) throws IOException
    {
        // Step 1: check the arguments
        if (args.length != EXPECTED_ARGUMENT_COUNT)
        {
            System.err.println("usage: ClientOrderPHMN <input> <output> <minUtil> <minPer> "
                    + "<maxPer> <minAvg> <maxAvg>");
            System.exit(EXIT_USAGE);
        }
        String input_path  = args[0];                 // database in SPMF utility format
        String output_path = args[1];                 // file that receives the patterns
        int[]  thresholds  = new int[5];              // minUtil, minPer, maxPer, minAvg, maxAvg
        for (int k = 0; k < thresholds.length; k++)
        {
            thresholds[k] = Integer.parseInt(args[k + 2]);
        }

        // Step 2: report which build of AlgoPHMN the class path selected, and refuse to run a
        //         class without the E8 counters before it can overwrite the output file
        String origin = locateClass(AlgoPHMN.class);
        System.out.println("AlgoPHMN loaded from: " + origin);
        for (String name : COUNTER_NAMES)
        {
            if (!hasCounter(name))
            {
                System.err.println("AlgoPHMN has no counter '" + name + "'. Put build/e8_a, "
                        + "build/e8_b or build/e8_c before spmf.jar on the class path.");
                System.exit(EXIT_USAGE);
            }
        }

        // Step 3: run plain PHMN exactly as the SPMF command line does
        AlgoPHMN algorithm = new AlgoPHMN();
        algorithm.runAlgorithm(false, input_path, output_path, thresholds[0], thresholds[1],
                thresholds[2], thresholds[3], thresholds[4]);
        algorithm.printStats();

        // Step 4: read the counters, whose presence step 2 has already checked
        long[] counters = new long[COUNTER_NAMES.length];
        for (int k = 0; k < COUNTER_NAMES.length; k++)
        {
            counters[k] = readCounter(algorithm, COUNTER_NAMES[k]);
        }

        // Step 5: print one machine-readable line and check the invariant
        StringBuilder line = new StringBuilder("E8 RESULT build=" + variantName(origin));
        for (int k = 0; k < COUNTER_NAMES.length; k++)
        {
            line.append(' ').append(COUNTER_NAMES[k]).append('=').append(counters[k]);
        }
        boolean invariant_holds = counters[1] == counters[2] + counters[3] + counters[0];
        line.append(" invariant=").append(invariant_holds ? "OK" : "FAILED");
        System.out.println(line);
        if (!invariant_holds)
        {
            System.exit(EXIT_INVARIANT_FAILED);
        }
    }

    /**
     * Finds the folder or archive a class was loaded from.
     *
     * @param type the class to locate
     * @return the location as a file system path, or "unknown" when the JVM does not report one
     */
    private static String locateClass(Class<?> type)
    {
        // Step 1: a class from the boot class path may have no code source
        CodeSource source = type.getProtectionDomain().getCodeSource();
        if (source == null || source.getLocation() == null)
        {
            return "unknown";
        }
        // Step 2: the location is a URL, so a folder name with spaces or accents arrives escaped;
        //         turn it back into a file system path
        try
        {
            return Paths.get(source.getLocation().toURI()).toString();
        }
        catch (URISyntaxException exception)
        {
            return source.getLocation().toString();
        }
    }

    /**
     * Derives a short build name from the location of the class.
     *
     * @param origin the location returned by {@link #locateClass(Class)}
     * @return the last folder name, for example "e8_a", or the whole location if it has none
     */
    private static String variantName(String origin)
    {
        // Step 1: drop a trailing separator, then keep the last path element
        String trimmed = origin.replace('\\', '/');
        if (trimmed.endsWith("/"))
        {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        int slash = trimmed.lastIndexOf('/');
        return slash >= 0 ? trimmed.substring(slash + 1) : trimmed;
    }

    /**
     * Tells whether the loaded AlgoPHMN has a public numeric counter of the given name.
     *
     * @param name the name of the field
     * @return true if the field exists and holds an int or a long
     */
    private static boolean hasCounter(String name)
    {
        // Step 1: look the field up by name and accept only an int or a long
        try
        {
            Class<?> type = AlgoPHMN.class.getField(name).getType();
            return type == int.class || type == long.class;
        }
        catch (NoSuchFieldException exception)
        {
            return false;
        }
    }

    /**
     * Reads a public numeric counter of the algorithm by name.
     *
     * @param algorithm the algorithm after its run
     * @param name the name of the field, already checked by {@link #hasCounter(String)}
     * @return the value of the field
     */
    private static long readCounter(AlgoPHMN algorithm, String name)
    {
        // Step 1: read the field of this instance and widen it to long
        try
        {
            Field field = AlgoPHMN.class.getField(name);
            return ((Number) field.get(algorithm)).longValue();
        }
        catch (NoSuchFieldException | IllegalAccessException exception)
        {
            throw new IllegalStateException("counter " + name + " cannot be read", exception);
        }
    }
}
