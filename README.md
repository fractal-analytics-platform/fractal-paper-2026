# fractal-paper-2026

Fractal 2026 paper supplementary code

Fractal workflows can be found in fractal_paper_2026/workflows. Some workflows require additional setting files (condition tables, illumination correction profiles, classifiers etc.). These files are available in subfolders of the workflow folder. The workflows would need to be adapted to point to the local location of those files on a given Fractal deployment.

Code for quality-control, analysis and plotting is available in subfolders for relevant figures.

## Installation

This project is managed by [pixi](https://pixi.sh).
You can install the package in development mode using:

```bash
git clone https://github.com/jluethi/fractal-paper-2026
cd fractal-paper-2026

pixi run pre-commit-install
pixi run postinstall
```
