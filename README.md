# 3d-scan-cleaner
Script to orient, clean, normalize, and fill holes in 3D scans.

Before             |  After
:-------------------------:|:-------------------------:
![](images/before.png)  |  ![](images/after.png)

## Installation 

To use, clone the repo and then install the requirements via pip:

```bash
virtualenv -p python3 env
source env/bin/activate
pip install -r requirements.txt
```

Tested with ubuntu18.04 and python3.6. 

## Usage

To test your installation run:

```bash
python clean.py examples/00007.ply out.ply --verbose
```

The following arguments can be passed to the script:

```bash
usage: clean.py [-h] [--normalize] [--no_reorient] [--no_close_holes]
                [--no_fix_winding] [--keep_all] [--verbose]
                [--ransac_threshold RANSAC_THRESHOLD]
                [--plane_offset PLANE_OFFSET] [--trim TRIM]
                input output

positional arguments:
  input                 Path to the input file.
  output                Path to the output file.

optional arguments:
  -h, --help            show this help message and exit
  --normalize           If passed, will scale and translate the mesh to the
                        center of a unit cube.
  --no_reorient         If passed, will not reorient the mesh according to the
                        ground plane.
  --no_close_holes      If passed will not attempt to fill holes in the
                        cleaned model.
  --no_fix_winding      If passed will not fix the winding of the input mesh.
  --keep_all            If passed, keep all connected components after
                        removing extraneousgeometry. Else will only keep the
                        largest connected component.
  --verbose             Print out more detailed status information.
  --ransac_threshold RANSAC_THRESHOLD
                        Threshold distance from the plane which is considered
                        inlier.
  --plane_offset PLANE_OFFSET
                        Distance to offset the plane before discarding points
                        below theplane.
  --trim TRIM           Size of the unit cube used to discard extraneous
                        geometry. This will work even if the normalize flag is
                        not passed.
```
