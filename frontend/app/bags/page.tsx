import BagsPageClient from "./bags-page-client";

type BagsPageSearchParams = Promise<{
  bag_type?: string | string[];
  status?: string | string[];
  bag_ref_contains?: string | string[];
}>;

function getSingleValue(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

export default async function BagsPage({
  searchParams,
}: {
  searchParams: BagsPageSearchParams;
}) {
  const params = await searchParams;

  return (
    <BagsPageClient
      initialBagType={getSingleValue(params.bag_type)}
      initialStatus={getSingleValue(params.status)}
      initialBagRefContains={getSingleValue(params.bag_ref_contains)}
    />
  );
}
