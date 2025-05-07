#!/bin/bash

YAML_FILE="ci.yaml"
OPERATOR_NAME=$(basename "$(pwd)")
TOPDIR=$(dirname "$(dirname "$(pwd)")")

# Extract mappings using yq with structured formatting
mappings=$("$TOPDIR"/bin/yq eval -o=json '.fbc.catalog_mapping[]' "$YAML_FILE" | jq -c '.')

# Helper: Determine if version is >= v4.17
requires_migrate_level() {
    local version="${1#v}"
    major=${version%%.*}
    minor=${version#*.}
    if [[ "$major" -gt 4 ]] || { [[ "$major" -eq 4 ]] && [[ "$minor" -ge 17 ]]; }; then
        return 0
    else
        return 1
    fi
}

# Helper: Render and distribute output
render_and_distribute() {
    local template_name="$1"
    local type="$2"
    local use_migrate="$3"
    shift 3
    local catalogs=("$@")

    local cmd=("$TOPDIR"/bin/opm alpha render-template)
    if [[ "$type" == "olm.template.basic" ]]; then
        cmd+=("basic")
    elif [[ "$type" == "olm.semver" ]]; then
        cmd+=("semver")
    else
        echo "Unknown type: $type"
        exit 1
    fi

    cmd+=("-o" "yaml")
    [[ "$use_migrate" == "true" ]] && cmd+=("--migrate-level" "bundle-object-to-csv-metadata")
    cmd+=("catalog-templates/$template_name")

    output=$("${cmd[@]}")
    if [[ $? -ne 0 ]]; then
        echo "❌ Error rendering $template_name"
        exit 1
    fi

    for catalog in "${catalogs[@]}"; do
        catalog_path="$TOPDIR/catalogs/$catalog/$OPERATOR_NAME"
        mkdir -p "$catalog_path"
        echo "$output" > "$catalog_path/catalog.yaml"
        echo " ✅ Rendered → $catalog_path/catalog.yaml"
    done
}

# Iterate over mappings
echo "$mappings" | while IFS= read -r mapping; do
    template_name=$(echo "$mapping" | jq -r '.template_name')
    type=$(echo "$mapping" | jq -r '.type')
    catalog_names=$(echo "$mapping" | jq -r '.catalog_names[]')

    echo "- Processing template: $template_name (Type: $type)"

    catalogs_with_migrate=()
    catalogs_without_migrate=()

    for catalog in $catalog_names; do
        if requires_migrate_level "$catalog"; then
            catalogs_with_migrate+=("$catalog")
        else
            catalogs_without_migrate+=("$catalog")
        fi
    done

    [[ ${#catalogs_without_migrate[@]} -gt 0 ]] && \
        render_and_distribute "$template_name" "$type" false "${catalogs_without_migrate[@]}"

    [[ ${#catalogs_with_migrate[@]} -gt 0 ]] && \
        render_and_distribute "$template_name" "$type" true "${catalogs_with_migrate[@]}"
done
