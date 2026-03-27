# Re-export facade — all existing callers use `from . import crud` then `crud.some_function(db)`.
# This module re-exports every public symbol from the 5 domain modules so those call sites
# continue to work without modification.

from .crud_status import (  # noqa: F401
    _now,
    _as_utc,
    _derive_bag_status_from_caches,
    _event_time_by_type,
    _derive_bag_status_from_history,
    _bag_history_snapshot,
    _sync_bag_status,
    _record_bag_event,
    _resolve_bag,
    _bag_lineage_options,
    _build_descendant_bags,
)

from .crud_reference import (  # noqa: F401
    list_fill_profiles,
    create_fill_profile,
    list_substrate_recipe_versions,
    create_substrate_recipe_version,
    list_spawn_recipes,
    create_spawn_recipe,
    list_mix_lots,
    create_mix_lot,
    list_species,
    create_species,
    update_species,
    list_liquid_cultures,
    create_liquid_culture,
    list_grain_types,
    create_grain_type,
    update_grain_type,
    list_ingredients,
    create_ingredient,
    update_ingredient,
    list_ingredient_lots,
    create_ingredient_lot,
    create_pasteurization_run,
    list_pasteurization_runs,
    get_pasteurization_run,
    update_pasteurization_run,
    create_sterilization_run,
    list_sterilization_runs,
    get_sterilization_run,
    update_sterilization_run,
)

from .crud_reporting import (  # noqa: F401
    calculate_bio_efficiency,
    _is_contaminated,
    _bag_payload,
    _build_substrate_metrics_row,
    _build_lineage_row,
    _summarize_bags,
    _summarize_substrate_metric_rows,
    get_sterilization_run_detail,
    get_pasteurization_run_detail,
    get_production_report,
)

from .crud_bags import (  # noqa: F401
    list_bag_status_events,
    create_spawn_bags,
    create_substrate_bags,
    get_bag,
    list_bags,
    get_bag_detail,
    update_bag_incubation_start,
    update_bag_ready,
    update_bag_fruiting_start,
    update_bag_disposal,
    update_bag_actual_dry_weight,
    inoculate_spawn_bags,
    create_inoculation_batch,
    create_inoculation,
    get_inoculation_for_substrate_bag,
    list_substrate_bags_inoculated_by,
    create_harvest_event,
    list_harvest_events_for_bag,
    get_bag_total_harvest_kg,
)

from .crud_dashboard import (  # noqa: F401
    get_dashboard_overview,
)
