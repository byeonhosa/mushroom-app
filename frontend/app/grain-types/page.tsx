"use client";

import { ReferenceList } from "../../lib/reference-list";
import { useCurrentUser } from "../../lib/session";

export default function GrainTypesPage() {
  const canEdit = useCurrentUser().role === "admin";

  return (
    <>
      <div className="card">
        <h1>Grain Types</h1>
        <p>
          The grains spawn is made on. A sterilization run and a purchased spawn lot each name one.
          {!canEdit && " Only an administrator can change them."}
        </p>
      </div>
      <ReferenceList
        title="Grain types"
        path="/grain-types"
        idKey="grain_type_id"
        noun="grain type"
        canEdit={canEdit}
        fields={[
          { key: "name", label: "Name", required: true, placeholder: "Rye, millet, sorghum" },
          { key: "notes", label: "Notes" },
        ]}
      />
    </>
  );
}
