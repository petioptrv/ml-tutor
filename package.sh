# Package the ml-tutor directory into a zip file, ignoring all files and directories that start with a dot, as well
# as __pycache__ directories.
# Usage: ./package.sh
cd ml-tutor && zip -r ../ml-tutor.ankiaddon * -x "*/\.*" -x "*/__pycache__/*" -x "*/meta.json"
