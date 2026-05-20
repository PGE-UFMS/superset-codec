import io
import re
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

_COMMENTS: dict[str, dict[str, str]] = {
    "databases": {
        "database_name":        "Connection name displayed in Superset",
        "sqlalchemy_uri":       "SQLAlchemy connection URI. Use ${VAR} for sensitive values",
        "expose_in_sqllab":     "Make this connection available in SQL Lab",
        "allow_run_async":      "Allow asynchronous query execution",
        "allow_cvas":           "Allow creation of Virtual Datasets (CVAS)",
        "allow_dml":            "Allow DML operations (INSERT, UPDATE, DELETE)",
        "allow_file_upload":    "Allow CSV/Excel file uploads",
        "configuration_method": "Configuration method (sqlalchemy_form or dynamic_form)",
        "driver":               "SQLAlchemy driver",
        "engine":               "Database engine",
    },
    "datasets": {
        "database":              "Superset connection name (must exist in databases/)",
        "schema":                "Schema or database within the connection",
        "table_name":            "Table or view name",
        "main_dttm_col":         "Default datetime column for time filters",
        "sql":                   "Custom SQL query (empty = use the table directly)",
        "filter_select_enabled": "Enable filter-by-selection in charts",
        "is_sqllab_view":        "Dataset created via SQL Lab",
        "offset":                "Timezone offset in hours",
        "description":           "Dataset description",
    },
    "charts": {
        "slice_name":       "Chart name displayed on the dashboard",
        "viz_type":         "Visualization type (e.g. big_number_total, echarts_timeseries_bar)",
        "datasource_table": "Source table/dataset (must exist in datasets/)",
        "params":           "Visualization-specific configuration",
        "description":      "Chart description",
    },
    "dashboards": {
        "dashboard_title":  "Title displayed in Superset",
        "slug":             "Unique identifier used in the URL and embedding",
        "published":        "Visible to all users (false = admins only)",
        "charts":           "Chart list with grid positions (row/col/width/height)",
        "native_filters":   "Native filters applied to the dashboard",
        "description":      "Dashboard description",
    },
}


def _to_commented_map(data: dict, comments: dict[str, str]) -> CommentedMap:
    cm = CommentedMap(data)
    for key, comment in comments.items():
        if key in cm:
            cm.yaml_set_comment_before_after_key(key, before=comment)
    return cm


def write(resources_dir: Path, resource_type: str, name: str, data: dict) -> Path:
    target_dir = resources_dir / resource_type
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = re.sub(r"[^\w\-]", "_", name).lower() + ".yaml"
    path = target_dir / filename

    comments = _COMMENTS.get(resource_type, {})
    doc = _to_commented_map(data, comments) if comments else data

    yaml = YAML()
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    yaml.width = 120

    buf = io.StringIO()
    yaml.dump(doc, buf)
    path.write_text(buf.getvalue(), encoding="utf-8")
    return path
