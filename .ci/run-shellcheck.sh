#!/bin/bash
export LC_ALL="C"

# how many shell scripts we pass to shellcheck at a time
export SC_BATCH=1

# how many shellcheck processes we run in parallel
export SC_JOBS=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)

# how long we wait (wall-clock time) for a single shellcheck process to finish
export SC_TIMEOUT=30

# options passed to csgrep while post-processing the results
CSGREP_OPTS=(
    --mode=json
    --event='error|warning'
    --remove-duplicates
    --embed-context=3
)

# create a temporary directory for shellcheck results
export sc_int_dir=$(mktemp -d /tmp/tmp-run-sc.XXXXXXXXXX)
trap "rm -rf '$sc_int_dir'" EXIT
touch "${sc_int_dir}/empty.json"

# implementation of the script that filters shell scripts
filter_shell_scripts() {
    for i in "$@"; do
        # match by file name suffix
        if [[ "$i" =~ ^.*\.(ash|bash|bats|dash|ksh|sh)$ ]]; then
            echo "$i"
            printf . >&2
            continue
        fi

        # match by shebang (executable files only)
        RE_SHEBANG='^\s*((#|!)|(#\s*!)|(!\s*#))\s*(/usr(/local)?)?/bin/(env\s+)?(ash|bash|bats|dash|ksh|sh)\b'
        if test -x "$i" && head -n1 "$i" | grep --text -E "$RE_SHEBANG" >/dev/null; then
            echo "$i"
            printf . >&2
        fi
    done
}

# store a script that filters shell scripts to a variable
FILTER_SCRIPT="$(declare -f filter_shell_scripts)
filter_shell_scripts"' "$@"'

# function that creates a separate JSON file if shellcheck detects anything
wrap_shellcheck() {
    dst="${sc_int_dir}/sc-$$.json"
    (set -x && timeout ${SC_TIMEOUT} shellcheck --format=json1 "$@" > "$dst") \
        && rm -f "$dst"
}

# store a script that filters shell scripts to a variable
SC_WRAP_SCRIPT="$(declare -f wrap_shellcheck)
wrap_shellcheck"' "$@"'

# find all shell scripts and run shellcheck on them
printf "Looking for shell scripts..." >&2
find "$@" -type f -print0 \
    | xargs -0 /bin/bash -c "$FILTER_SCRIPT" "$0" \
    | { sort -uV && echo " done" >&2; } \
    | xargs -rn ${SC_BATCH} --max-procs=${SC_JOBS} \
    /bin/bash -c "$SC_WRAP_SCRIPT" "$0"

# process all results as configured with CSGREP_OPTS
csgrep "${CSGREP_OPTS[@]}" "${sc_int_dir}"/*.json
