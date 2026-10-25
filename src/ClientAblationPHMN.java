import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintStream;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

import ca.pfv.spmf.algorithms.frequentpatterns.phmn_plus.AlgoPHMN;

/**
 * Ablation experiment E0-E5 for the PHMN and PHMN+ algorithms of SPMF.
 *
 * <p>The goal is to measure how much each pruning strategy of PHMN actually contributes, by
 * switching the strategies off one at a time and running the algorithm again on the same data.
 * Two kinds of question are answered at once:</p>
 *
 * <ul>
 *   <li>How much speed does a strategy buy? Compare time and candidate count against E0.</li>
 *   <li>Is the strategy correct? A pure speed-up strategy must return exactly the same patterns.
 *       If switching it off changes the result set, the strategy is losing patterns.</li>
 * </ul>
 *
 * <p>The three switches live inside {@code AlgoPHMN} and are not reachable from the normal
 * {@code java -jar spmf.jar run PHMN ...} command line, which is why this client exists.
 * EUCP and ESCP have public setters; LA-prune has none, so it is set through reflection.</p>
 *
 * <p>How to run, from the project root directory:</p>
 *
 * <pre>
 * java -cp tools/spmf/spmf.jar src/ClientAblationPHMN.java &lt;input&gt; &lt;outputDir&gt; &lt;minUtil&gt; &lt;minPer&gt; &lt;maxPer&gt; &lt;minAvg&gt; &lt;maxAvg&gt;
 *
 * java -cp tools/spmf/spmf.jar src/ClientAblationPHMN.java data/PHMN_Table1_example.txt output 30 1 5 1 3
 * </pre>
 *
 * <p>Always pass relative paths. SPMF decodes command line arguments with the native Windows
 * encoding, so a path containing Vietnamese characters arrives corrupted and the input file is
 * reported as missing.</p>
 */
public class ClientAblationPHMN
{
    /** How many times each configuration runs; the fastest run is reported. */
    private static final int REPEAT_COUNT = 3;

    /** Identifier of the configuration that all other configurations are compared against. */
    private static final String BASELINE_ID = "E0";

    /** Number of command line arguments the client expects. */
    private static final int EXPECTED_ARGUMENT_COUNT = 7;

    /**
     * One ablation configuration, that is one row of the result table.
     */
    private static class Config
    {
        /** Short identifier shown in the result table, for example "E1". */
        String id;
        /** Human readable description of what is switched off. */
        String label;
        /** True runs PHMN+, false runs plain PHMN. */
        boolean use_improve;
        /** True keeps the EUCP strategy enabled. */
        boolean enable_eucp;
        /** True keeps the ESCP strategy enabled. */
        boolean enable_escp;
        /** True keeps the LA-prune strategy enabled. */
        boolean enable_la_prune;

        /**
         * Builds one configuration.
         *
         * @param id short identifier shown in the result table
         * @param label human readable description of what is switched off
         * @param use_improve true runs PHMN+, false runs plain PHMN
         * @param enable_eucp true keeps the EUCP strategy enabled
         * @param enable_escp true keeps the ESCP strategy enabled
         * @param enable_la_prune true keeps the LA-prune strategy enabled
         */
        Config(String id, String label, boolean use_improve,
               boolean enable_eucp, boolean enable_escp, boolean enable_la_prune)
        {
            this.id = id;
            this.label = label;
            this.use_improve = use_improve;
            this.enable_eucp = enable_eucp;
            this.enable_escp = enable_escp;
            this.enable_la_prune = enable_la_prune;
        }
    }

    /**
     * The measurements collected from one configuration.
     */
    private static class Result
    {
        /** Number of periodic high utility itemsets written to the output file. */
        int pattern_count;
        /** Number of calls to construct(), comparable with the list counts reported in the paper. */
        int candidate_count;
        /** Fastest running time over all repetitions, in milliseconds. */
        double time_ms;
        /** Peak memory reported by SPMF, in megabytes. */
        double memory_mb;
        /** The patterns themselves, used to check whether two configurations agree. */
        Set<String> patterns;
    }

    /**
     * Entry point. Runs every configuration in turn and prints one result table.
     *
     * @param args input file, output directory, then minUtil, minPer, maxPer, minAvg, maxAvg
     * @throws Exception if the input cannot be read or the output cannot be written
     */
    public static void main(String[] args) throws Exception
    {
        // Step 1: check the command line.
        if (args.length != EXPECTED_ARGUMENT_COUNT)
        {
            printUsage();
            return;
        }

        String input_path = args[0];
        String output_dir = args[1];
        int[] thresholds = new int[5];
        for (int i = 0; i < thresholds.length; i++)
        {
            thresholds[i] = Integer.parseInt(args[i + 2]);
        }

        // Step 2: make sure the output directory exists.
        File output_folder = new File(output_dir);
        if (!output_folder.exists())
        {
            output_folder.mkdirs();
        }

        // Step 3: describe the configurations to compare.
        List<Config> configs = new ArrayList<>();
        configs.add(new Config("E0", "PHMN full",            false, true,  true,  true));
        configs.add(new Config("E1", "PHMN without EUCP",    false, false, true,  true));
        configs.add(new Config("E2", "PHMN without ESCP",    false, true,  false, true));
        configs.add(new Config("E3", "PHMN without LA-prune", false, true, true,  false));
        configs.add(new Config("E4", "PHMN without all three", false, false, false, false));
        configs.add(new Config("E5", "PHMN+ full",           true,  true,  true,  true));

        // Step 4: run them and keep the measurements.
        Map<String, Result> results = new LinkedHashMap<>();
        for (Config config : configs)
        {
            System.out.println("running " + config.id + " : " + config.label);
            results.put(config.id, runConfiguration(config, input_path, output_dir, thresholds));
        }

        // Step 5: report.
        printHeader(input_path, thresholds);
        printTable(configs, results);
        printAgreementCheck(configs, results);
    }

    /**
     * Runs one configuration several times and returns the measurements of the fastest run.
     *
     * @param config the configuration to run
     * @param input_path the transaction database
     * @param output_dir the directory where the pattern file is written
     * @param thresholds minUtil, minPer, maxPer, minAvg, maxAvg in this order
     * @return the collected measurements
     * @throws Exception if the algorithm fails or its output cannot be read
     */
    private static Result runConfiguration(Config config, String input_path,
                                           String output_dir, int[] thresholds) throws Exception
    {
        String output_path = output_dir + File.separator + "ablation_" + config.id + ".txt";
        Result result = new Result();
        result.time_ms = Double.MAX_VALUE;

        for (int repetition = 0; repetition < REPEAT_COUNT; repetition++)
        {
            AlgoPHMN algorithm = new AlgoPHMN();

            // Step 1: the two strategies that expose a public setter.
            algorithm.setEnableEUCP(config.enable_eucp);
            algorithm.setEnableESCP(config.enable_escp);

            // Step 2: LA-prune has no setter, so write its field directly. The field is package
            // private, which reflection can reach because the jar sits on the class path.
            Field la_prune_field = AlgoPHMN.class.getDeclaredField("ENABLE_LA_PRUNE");
            la_prune_field.setAccessible(true);
            la_prune_field.setBoolean(algorithm, config.enable_la_prune);

            // Step 3: run with the console muted. AlgoPHMN prints a counter every ten thousand
            // candidates, and that printing would be measured as part of the running time.
            PrintStream console = System.out;
            System.setOut(new PrintStream(OutputStream.nullOutputStream()));
            try
            {
                algorithm.runAlgorithm(config.use_improve, input_path, output_path,
                        thresholds[0], thresholds[1], thresholds[2], thresholds[3], thresholds[4]);
            }
            finally
            {
                System.setOut(console);
            }

            // Step 4: keep the fastest run. Pattern and candidate counts do not vary between runs.
            if (algorithm.totalExecutionTime < result.time_ms)
            {
                result.time_ms = algorithm.totalExecutionTime;
            }
            result.pattern_count = algorithm.phuiCount;
            result.candidate_count = algorithm.candidateCount;
            result.memory_mb = algorithm.maximumMemoryUsage;
        }

        result.patterns = readPatterns(output_path);
        return result;
    }

    /**
     * Reads a pattern file produced by SPMF into a set of normalised strings.
     *
     * <p>Items are sorted by identifier so that two configurations which find the same itemset in
     * a different internal order still produce the same string.</p>
     *
     * @param output_path the pattern file to read
     * @return one entry per pattern, of the form "1 3 4 => 48"
     * @throws IOException if the file cannot be read
     */
    private static Set<String> readPatterns(String output_path) throws IOException
    {
        Set<String> patterns = new TreeSet<>();

        for (String line : Files.readAllLines(Path.of(output_path), StandardCharsets.UTF_8))
        {
            String trimmed = line.trim();
            if (trimmed.isEmpty() || trimmed.charAt(0) == '@')
            {
                continue;
            }

            // A line looks like: 1 4 3 #UTIL: 48 #SUP: 3 #MINPER: 1 #MAXPER: 2 #AVGPER: 2.0
            String[] segments = trimmed.split("#");
            String[] item_text = segments[0].trim().split("\\s+");
            int[] items = new int[item_text.length];
            for (int i = 0; i < item_text.length; i++)
            {
                items[i] = Integer.parseInt(item_text[i]);
            }
            java.util.Arrays.sort(items);

            String utility = segments[1].substring(segments[1].indexOf(':') + 1).trim();

            StringBuilder key = new StringBuilder();
            for (int item : items)
            {
                key.append(item).append(' ');
            }
            key.append("=> ").append(utility);
            patterns.add(key.toString());
        }

        return patterns;
    }

    /**
     * Prints the experiment settings above the result table.
     *
     * @param input_path the transaction database that was mined
     * @param thresholds minUtil, minPer, maxPer, minAvg, maxAvg in this order
     */
    private static void printHeader(String input_path, int[] thresholds)
    {
        System.out.println();
        System.out.println("## Ablation PHMN / PHMN+");
        System.out.println();
        System.out.println("- data: " + input_path);
        System.out.println("- minUtil=" + thresholds[0] + "  minPer=" + thresholds[1]
                + "  maxPer=" + thresholds[2] + "  minAvg=" + thresholds[3]
                + "  maxAvg=" + thresholds[4]);
        System.out.println("- each configuration ran " + REPEAT_COUNT
                + " times, the fastest time is reported");
        System.out.println();
    }

    /**
     * Prints the measurements as a markdown table ready to paste into the report.
     *
     * @param configs the configurations, in the order they should appear
     * @param results the measurements, indexed by configuration identifier
     */
    private static void printTable(List<Config> configs, Map<String, Result> results)
    {
        Result baseline = results.get(BASELINE_ID);

        System.out.println("| Code | Configuration | Patterns | Candidates | vs E0 | Time (ms) | vs E0 | Memory (MB) |");
        System.out.println("|---|---|---|---|---|---|---|---|");

        for (Config config : configs)
        {
            Result result = results.get(config.id);
            System.out.printf("| %s | %s | %d | %d | %s | %.0f | %s | %.1f |%n",
                    config.id,
                    config.label,
                    result.pattern_count,
                    result.candidate_count,
                    formatRatio(result.candidate_count, baseline.candidate_count),
                    result.time_ms,
                    formatRatio(result.time_ms, baseline.time_ms),
                    result.memory_mb);
        }
        System.out.println();
    }

    /**
     * Formats a measurement as a percentage change against the baseline.
     *
     * @param value the measurement of the current configuration
     * @param baseline_value the measurement of the baseline configuration
     * @return a string such as "+34%", or "-" when the baseline is zero
     */
    private static String formatRatio(double value, double baseline_value)
    {
        if (baseline_value == 0)
        {
            return "-";
        }
        double change = (value - baseline_value) / baseline_value * 100d;
        return String.format("%+.0f%%", change);
    }

    /**
     * Checks that every configuration found exactly the same patterns as the baseline.
     *
     * <p>All three strategies are pure speed-up strategies, so any difference means one of them
     * is unsound on this data and is discarding valid patterns.</p>
     *
     * @param configs the configurations that were run
     * @param results the measurements, indexed by configuration identifier
     */
    private static void printAgreementCheck(List<Config> configs, Map<String, Result> results)
    {
        Result baseline = results.get(BASELINE_ID);
        System.out.println("### Do all configurations agree with " + BASELINE_ID + " ?");
        System.out.println();

        for (Config config : configs)
        {
            if (config.id.equals(BASELINE_ID))
            {
                continue;
            }

            Set<String> found = results.get(config.id).patterns;
            Set<String> missing = new TreeSet<>(baseline.patterns);
            missing.removeAll(found);
            Set<String> extra = new TreeSet<>(found);
            extra.removeAll(baseline.patterns);

            if (missing.isEmpty() && extra.isEmpty())
            {
                System.out.println("- " + config.id + " : same patterns, so the strategy is a pure speed-up here");
            }
            else
            {
                System.out.println("- " + config.id + " : DIFFERENT. "
                        + missing.size() + " pattern(s) only in " + BASELINE_ID + ", "
                        + extra.size() + " pattern(s) only in " + config.id);
                printSample("    only in " + BASELINE_ID + ": ", missing);
                printSample("    only in " + config.id + ": ", extra);
            }
        }
        System.out.println();
    }

    /**
     * Prints at most three patterns of a set, as an example of a disagreement.
     *
     * @param prefix the text printed before the examples
     * @param patterns the set to take the examples from
     */
    private static void printSample(String prefix, Set<String> patterns)
    {
        if (patterns.isEmpty())
        {
            return;
        }
        StringBuilder line = new StringBuilder(prefix);
        int shown = 0;
        for (String pattern : patterns)
        {
            if (shown == 3)
            {
                line.append("...");
                break;
            }
            line.append('[').append(pattern).append("] ");
            shown++;
        }
        System.out.println(line);
    }

    /**
     * Prints how to call this client.
     */
    private static void printUsage()
    {
        System.out.println("Ablation experiment for PHMN and PHMN+.");
        System.out.println();
        System.out.println("Usage, from the project root directory:");
        System.out.println("  java -cp tools/spmf/spmf.jar src/ClientAblationPHMN.java"
                + " <input> <outputDir> <minUtil> <minPer> <maxPer> <minAvg> <maxAvg>");
        System.out.println();
        System.out.println("Example:");
        System.out.println("  java -cp tools/spmf/spmf.jar src/ClientAblationPHMN.java"
                + " data/PHMN_Table1_example.txt output 30 1 5 1 3");
        System.out.println();
        System.out.println("Use relative paths only. SPMF cannot open a path that contains"
                + " Vietnamese characters.");
    }
}
