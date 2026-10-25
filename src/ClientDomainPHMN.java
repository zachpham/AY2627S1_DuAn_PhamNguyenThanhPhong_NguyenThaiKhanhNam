import java.io.File;
import java.io.OutputStream;
import java.io.PrintStream;

import ca.pfv.spmf.algorithms.frequentpatterns.phmn_plus.AlgoPHMN;

/**
 * One single measured run of PHMN, used by the study of the optimal application domain (C11).
 *
 * <p>This client answers the two questions the supervisor asked: which data characteristics suit
 * the algorithm, and in which parameter region it performs well. It therefore does exactly one
 * run and prints one line of numbers, so that a driver script can sweep over many databases and
 * many threshold settings without parsing the chatty output of the SPMF command line.</p>
 *
 * <p>How to run, from the project root directory:</p>
 *
 * <pre>
 * java -cp tools/spmf/spmf.jar src/ClientDomainPHMN.java &lt;input&gt; &lt;output&gt; &lt;minUtil&gt; &lt;minPer&gt; &lt;maxPer&gt; &lt;minAvg&gt; &lt;maxAvg&gt;
 * </pre>
 *
 * <p>The single output line has the form:</p>
 *
 * <pre>
 * RESULT patterns=5 candidates=6 time_ms=2 memory_mb=17.3
 * </pre>
 *
 * <p>Always pass relative paths. SPMF decodes command line arguments with the native Windows
 * encoding, so a path containing Vietnamese characters arrives corrupted.</p>
 */
public class ClientDomainPHMN
{
    /** How many times the run is repeated; the fastest time is reported. */
    private static final int REPEAT_COUNT = 3;

    /** Number of command line arguments the client expects. */
    private static final int EXPECTED_ARGUMENT_COUNT = 7;

    /**
     * Entry point. Runs PHMN once on the given data and prints one line of measurements.
     *
     * @param args input file, output file, then minUtil, minPer, maxPer, minAvg, maxAvg
     * @throws Exception if the input cannot be read or the output cannot be written
     */
    public static void main(String[] args) throws Exception
    {
        // Step 1: check the command line.
        if (args.length != EXPECTED_ARGUMENT_COUNT)
        {
            System.out.println("Usage: java -cp tools/spmf/spmf.jar src/ClientDomainPHMN.java"
                    + " <input> <output> <minUtil> <minPer> <maxPer> <minAvg> <maxAvg>");
            return;
        }

        String input_path = args[0];
        String output_path = args[1];
        int[] thresholds = new int[5];
        for (int i = 0; i < thresholds.length; i++)
        {
            thresholds[i] = Integer.parseInt(args[i + 2]);
        }

        // Step 2: make sure the output directory exists.
        File output_file = new File(output_path);
        if (output_file.getParentFile() != null && !output_file.getParentFile().exists())
        {
            output_file.getParentFile().mkdirs();
        }

        int pattern_count = 0;
        int candidate_count = 0;
        double best_time_ms = Double.MAX_VALUE;
        double memory_mb = 0;

        // Step 3: run several times and keep the fastest. Counts do not vary between runs.
        for (int repetition = 0; repetition < REPEAT_COUNT; repetition++)
        {
            AlgoPHMN algorithm = new AlgoPHMN();

            // Mute the console: AlgoPHMN prints a counter every ten thousand candidates, and that
            // printing would otherwise be measured as part of the running time.
            PrintStream console = System.out;
            System.setOut(new PrintStream(OutputStream.nullOutputStream()));
            try
            {
                algorithm.runAlgorithm(false, input_path, output_path,
                        thresholds[0], thresholds[1], thresholds[2], thresholds[3], thresholds[4]);
            }
            finally
            {
                System.setOut(console);
            }

            if (algorithm.totalExecutionTime < best_time_ms)
            {
                best_time_ms = algorithm.totalExecutionTime;
            }
            pattern_count = algorithm.phuiCount;
            candidate_count = algorithm.candidateCount;
            memory_mb = algorithm.maximumMemoryUsage;
        }

        // Step 4: one machine readable line.
        System.out.printf("RESULT patterns=%d candidates=%d time_ms=%.0f memory_mb=%.1f%n",
                pattern_count, candidate_count, best_time_ms, memory_mb);
    }
}
