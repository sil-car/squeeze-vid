#!/bin/bash

file_path=$(readlink -f "$0")
root_dir=$(dirname $(dirname "$file_path"))
cd "${root_dir}"

usage="Usage: $0 [-h] | [-t] [-v]"
help="$usage

   -h   Print this help and exit.
   -t   Run unittest only. Don't check coverage.
   -v   Give verbose output.
"
executable="python3 -m coverage run --branch"
verbose=''
missing=''

while getopts ":htv" o; do
    case "${o}" in
        h)
            echo "$help"
            exit 0
            ;;
        t)
            executable="python3"
            ;;
        v)
            verbose='-v'
            missing='-m'
            ;;
        *)
            echo "$usage"
            exit 1
            ;;
    esac
done
shift $((OPTIND-1))

# Run tests.
${executable[@]} -m unittest discover "$verbose" -s tests
echo -e "\n"

# Show report when coverage is run.
if [[ "$executable" == "python3 -m coverage run --branch" ]]; then
    if [[ "$missing" ]]; then
        python3 -m coverage report "$missing"
    else
        python3 -m coverage report
    fi
fi

exit $?
