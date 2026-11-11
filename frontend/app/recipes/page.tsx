"use client";

import { ReferenceList } from "../../lib/reference-list";
import { useCurrentUser } from "../../lib/session";

export default function RecipesPage() {
  const canEdit = useCurrentUser().role === "admin";

  return (
    <>
      <div className="card">
        <h1>Recipes and fill profiles</h1>
        <p>
          What a run is made from. A sterilization run names a spawn recipe; a mix lot names a substrate recipe and a
          fill profile. Set these up once, before the first run.
          {!canEdit && " Only an administrator can change them."}
        </p>
      </div>

      <ReferenceList
        title="Spawn recipes"
        intro="How grain is prepared for spawn bags."
        path="/spawn-recipes"
        idKey="spawn_recipe_id"
        noun="spawn recipe"
        canEdit={canEdit}
        fields={[
          { key: "recipe_code", label: "Code", required: true, placeholder: "RYE-1", hint: "Capital letters, digits and hyphens." },
          { key: "notes", label: "Description", placeholder: "Rye berries, soaked 12 hours, 1% gypsum" },
        ]}
      />

      <ReferenceList
        title="Substrate recipes"
        intro="What goes into a substrate mix. A changed recipe is a new recipe: add it and deactivate the old one, so that earlier runs keep the recipe they were made with."
        path="/substrate-recipe-versions"
        idKey="substrate_recipe_version_id"
        noun="substrate recipe"
        canEdit={canEdit}
        fields={[
          { key: "name", label: "Name", required: true, placeholder: "Masters Mix" },
          { key: "recipe_code", label: "Code", required: true, placeholder: "MM", hint: "Capital letters, digits and hyphens." },
          { key: "notes", label: "Description", placeholder: "50% hardwood pellets, 50% soy hulls" },
        ]}
      />

      <ReferenceList
        title="Fill profiles"
        intro="How much goes into one bag. The dry weight is what biological efficiency is worked out from. Bags already created keep the weight they were created with."
        path="/fill-profiles"
        idKey="fill_profile_id"
        noun="fill profile"
        canEdit={canEdit}
        fields={[
          { key: "name", label: "Name", required: true, placeholder: "5 lb block" },
          { key: "target_dry_kg_per_bag", label: "Dry weight per bag", kind: "number", required: true, unit: "kg", hint: "In kilograms." },
          { key: "target_water_kg_per_bag", label: "Water per bag", kind: "number", required: true, unit: "kg", hint: "In kilograms." },
          { key: "notes", label: "Notes" },
        ]}
      />
    </>
  );
}
