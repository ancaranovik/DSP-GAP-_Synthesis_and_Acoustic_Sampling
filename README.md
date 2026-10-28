# DSP-GAP

Normal/Wheeze audio experiments on SPRSound BioCAS2022. The research question is whether sparsity-weighted selection of DSP-generated wheezes improves classification compared with event-uniform selection at the same augmentation budget.

The current code covers data audit, a subject-independent split, 2-second segments, and a Real Only baseline (40 log-mel means/stds + logistic regression). The generator and DSP-E/DSP-S comparison are not implemented yet. Test audio is not used for development.

## Notebooks

| Notebook | Purpose |
|---|---|
| [00](dsp/notebooks/00_kiem_tra_du_an.ipynb) | Check source folders, templates and kernel path; works before downloading data. |
| [01](dsp/notebooks/01_kiem_ke_du_lieu.ipynb) | Audit source metadata, labels, intervals, subjects and duplicates. |
| [02](dsp/notebooks/02_chia_tap_theo_nguoi.ipynb) | Split official training subjects into train/validation; keep inter-test separate. |
| [03](dsp/notebooks/03_tao_segment_va_kiem_tra.ipynb) | Create 2-second segments, verified context, zero padding and amplitude normalization. |
| [04](dsp/notebooks/04_baseline_real_only.ipynb) | Extract log-mel statistics and fit/evaluate logistic regression on train/validation. |

The algorithms are written directly in the notebook cells. Comments and explanations are in Vietnamese. GitHub can display the source without installing anything; saved outputs and audio are omitted.

## Setup

Use **Python 3.11** (checked with 3.11.9), Git, and a notebook interface. CPU is sufficient; no GPU, CUDA, FFmpeg or paid service is needed. Reserve about **3 GB of free disk space** for the environment, data cache and one preprocessing run; repeated runs need more space.

```sh
git clone https://github.com/ancaranovik/DSP-GAP-_Synthesis_and_Acoustic_Sampling.git
cd DSP-GAP-_Synthesis_and_Acoustic_Sampling
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dsp.txt
.\.venv\Scripts\python.exe -m pip install jupyterlab==4.6.4
.\.venv\Scripts\python.exe -m jupyterlab
```

macOS/Linux:

```sh
.venv/bin/python -m pip install -r requirements-dsp.txt
.venv/bin/python -m pip install jupyterlab==4.6.4
.venv/bin/python -m jupyterlab
```

In JupyterLab, select the Python kernel from this `.venv`. Alternatively, open the repository in VS Code with its Python/Jupyter extensions and select `.venv`; the separate JupyterLab install is then optional. Dependency versions were checked on Windows; other operating systems have not been tested.

## Download the data

Cloning this repository does **not** include the dataset or generated artifacts. Run from the repository root, using `.venv` Python:

```powershell
.\.venv\Scripts\python.exe dsp/scripts/download_biocas2022.py
```

On macOS/Linux, replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

The script downloads only BioCAS2022 and its source documentation from [SPRSound](https://github.com/SJTU-YONGFU-RESEARCH-GRP/SPRSound), pinned to commit `bca1e51422a42a042441010081519610ef3845d0`. It exports original Git bytes to `dsp/data/raw/` and writes `dsp/outputs/reports/download_biocas2022.json` with checksums. The exported data occupies about 449 MiB; Git also keeps a local download cache. Internet access to GitHub is required for the first download.

If a local Git checkout of SPRSound already contains that commit, pass `--source-repo /path/to/SPRSound` to reuse it. Existing raw files with different checksums are rejected; nothing is silently overwritten. A completed download manifest also prevents accidental re-download. Source dataset terms and attribution are retained in `dsp/data/raw/SPRSound_LICENSE` and `SPRSound_README.md`.

## Run in order

1. Open JupyterLab **from the repository root**. Run `00`, then `01` with **Restart Kernel and Run All Cells**.
2. Copy the `audit_...` Run ID printed by `01` into `AUDIT_ID` near the start of `02`. Save and run `02` from a fresh kernel.
3. Copy the printed `SPLIT_ID` from `02` into `03`. Save and run `03` from a fresh kernel.
4. Copy the printed `SEGMENT_ID` from `03` into `04`. Save and run `04` from a fresh kernel.

The IDs already shown in the notebooks refer to the author's local runs. **Replace them with your own IDs**; those output folders are deliberately not in Git. Each run creates a new folder and keeps earlier artifacts. Never select a different split to improve a score.

If the kernel starts outside the repository, set `PROJECT_PATH` to your clone's root in the first code cell. `FileNotFoundError` for an audit/split/segment folder usually means the previous notebook has not run or its output ID was not copied. A checksum failure should be investigated rather than bypassed. An `ERROR`/`REVIEW` in `01` must be resolved before continuing.

`waveforms.npy[i]` corresponds to `row_index=i` in `segments.csv`; subsequent notebooks read files, not variables left in another kernel. Reading test JSON metadata for the predefined partition/task is permitted; test waveforms, features and scores remain locked.

## Points under review

- **03:** valid length/padding differs substantially by class. This may give the classifier a shortcut; the degree of reliance still needs investigation.
- **04:** mean/std pooling discards temporal order. Conclusions are limited to this representation and classifier.

The development run selected lambda `1e-4` and obtained validation macro-F1 `0.6761` (Wheeze precision `0.3311`, recall `0.7903`). Validation was used to select lambda, so this is not an independent test result or evidence of a DSP-E/S benefit. These methodological points are awaiting supervisor feedback.

Raw audio, subject manifests, models, generated results, local working notes and proposals are excluded from this repository. No synthetic-data or clinical-validity claim is made by the current baseline.
