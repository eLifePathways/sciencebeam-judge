# ScienceBeam Judge

ScienceBeam Judge implements a JATS/TEI conversion [evaluation](evaluation.md).
It can be configured to handle other similar document types.

## Installation

```bash
pip install sciencebeam-judge
```

## CLI

### Evaluation to CSV

```bash
python -m sciencebeam_judge.evaluation_pipeline \
  --target-file-list=<path to target file list> \
  [--target-file-column=<column name>] \
  --prediction-file-list=<path to prediction file list> \
  [--prediction-file-column=<column name>] \
  --output-path=<output directory> \
  [--limit=<max file pair count>] \
  [--cloud] \
  [--num_workers=<number of workers>]
```

The default configuration files ([xml-mapping.conf](../sciencebeam_judge/resources/xml-mapping.conf),
[evaluation.conf](../sciencebeam_judge/resources/evaluation.conf),
[evaluation.yml](../sciencebeam_judge/resources/evaluation.yml))
are bundled with the package and used automatically.
They can be overridden with `--xml-mapping`, `--evaluation-config`, or `--evaluation-yaml-config`.

The output path will contain the following files:

- `results-*.csv`: The detailed evaluation of every field
- `summary-*.csv`: The overall evaluation
- `grobid-formatted-summary-*.txt`: The summary formatted à la GROBID

### Extract Fields

```bash
python -m sciencebeam_judge.extract_fields \
    --xml-file=<path to xml file> \
    --fields=<comma separated list of fields>
```

## Configuration

### XML Mapping

The [xml-mapping.conf](../sciencebeam_judge/resources/xml-mapping.conf) configures how fields
should be extracted from the XML. The default configuration contains mapping for JATS and TEI.

### Evaluation Configuration

The [evaluation.conf](../sciencebeam_judge/resources/evaluation.conf) allows further evaluation
details to be configured. For example the *scoring type* defines how a field should be evaluated
(e.g. `string` or `list`).

An additional [evaluation.yml](../sciencebeam_judge/resources/evaluation.yml) has the same
function but allows for more structured configuration.
