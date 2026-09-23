import { Activity, Building2, Database, Network, Users } from "lucide-react";
import { enterpriseApi, apiErrorMessage } from "../api/client";
import { Card, ErrorState, PageHeader, PageSkeleton } from "../components/ui";
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
  if (loading) return <PageSkeleton rows={3} />;
  if (error || !data) return <ErrorState message={apiErrorMessage(error)} retry={() => void reload()} />;
  const metrics = [
    ["Organizations", data.overview.organizations, Building2], ["Users", data.overview.users, Users],
    ["Scans", data.overview.scans, Activity], ["Assets", data.overview.assets, Database],
  ] as const;
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Enterprise administration"
        title="Admin dashboard"
        description={`${data.organization.name} identity, platform health, and tenant activity.`}
      />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map(([label, value, Icon]) => (
          <Card key={label} className="card-hover p-5">
            <Icon className="h-5 w-5 text-indigo-600" strokeWidth={1.75} />
            <p className="mt-4 font-mono text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{label}</p>
            <p className="mt-1 text-3xl font-bold tracking-tight text-zinc-950">{value}</p>
          </Card>
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <Card className="p-5">
          <p className="text-sm font-bold text-zinc-950">Organization users</p>
          <div className="mt-4 divide-y divide-zinc-100">
            {data.users.map((user) => (
              <div key={user.id} className="flex items-center justify-between py-3 text-sm">
                <div>
                  <p className="font-semibold text-zinc-900">{user.username}</p>
                  <p className="font-mono text-xs text-zinc-500">{user.email}</p>
                </div>
                <span className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 font-mono text-xs font-semibold capitalize text-indigo-700">
                  {user.role.replace("_", " ")}
                </span>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-5">
          <p className="text-sm font-bold text-zinc-950">System health</p>
          <div className="mt-4 space-y-2.5">
            {Object.entries(data.health)
              .filter(([key]) => key !== "scanners")
              .map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-center justify-between rounded border border-zinc-200 bg-zinc-50/50 px-4 py-3 text-sm"
                >
                  <span className="flex items-center gap-2 capitalize text-zinc-700 font-medium">
                    <Network className="h-4 w-4 text-zinc-400" />
                    {key.replace("_", " ")}
                  </span>
                  <span className="font-mono text-xs font-bold text-emerald-700">{String(value)}</span>
                </div>
              ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
