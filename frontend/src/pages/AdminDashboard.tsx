import { Activity, Building2, Database, Network, Users } from "lucide-react";
import { enterpriseApi, apiErrorMessage } from "../api/client";
import { Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAsync } from "../hooks/useAsync";

export function AdminDashboard() {
  const { data, error, loading, reload } = useAsync(
    async () => {
      const [overview, organization, users, health] = await Promise.all([
        enterpriseApi.overview(), enterpriseApi.organization(), enterpriseApi.users(), enterpriseApi.health(),
      ]);
      return { overview, organization, users, health };
    },
    [],
  );
  if (loading) return <LoadingState label="Loading enterprise administration" />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  const metrics = [
    ["Organizations", data.overview.organizations, Building2], ["Users", data.overview.users, Users],
    ["Scans", data.overview.scans, Activity], ["Assets", data.overview.assets, Database],
  ] as const;
  return <div className="space-y-8"><PageHeader eyebrow="Enterprise administration" title="Admin dashboard" description={`${data.organization.name} identity, platform health, and tenant activity.`} /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, Icon]) => <Card key={label} className="p-5"><Icon className="h-5 w-5 text-brand-300" /><p className="mt-5 text-xs text-slate-500">{label}</p><p className="mt-1 text-3xl font-bold text-white">{value}</p></Card>)}</div><div className="grid gap-5 xl:grid-cols-2"><Card className="p-5"><p className="font-semibold text-white">Organization users</p><div className="mt-4 divide-y divide-white/[0.05]">{data.users.map((user) => <div key={user.id} className="flex items-center justify-between py-3 text-sm"><div><p className="text-slate-200">{user.username}</p><p className="text-xs text-slate-600">{user.email}</p></div><span className="rounded-full bg-brand-400/10 px-3 py-1 text-xs capitalize text-brand-200">{user.role.replace("_", " ")}</span></div>)}</div></Card><Card className="p-5"><p className="font-semibold text-white">System health</p><div className="mt-4 space-y-3">{Object.entries(data.health).filter(([key]) => key !== "scanners").map(([key, value]) => <div key={key} className="flex items-center justify-between rounded-xl bg-white/[0.025] px-4 py-3 text-sm"><span className="flex items-center gap-2 capitalize text-slate-400"><Network className="h-4 w-4" />{key.replace("_", " ")}</span><span className="text-emerald-300">{String(value)}</span></div>)}</div></Card></div></div>;
}
