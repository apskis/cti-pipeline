interface StatTileProps {
  label: string;
  value: string;
  detail?: string;
}

const StatTile = ({ label, value, detail }: StatTileProps) => (
  <div className="rounded-lg bg-raised p-4">
    <p className="text-sm text-muted">{label}</p>
    <p className="mt-1 text-2xl font-medium">{value}</p>
    {detail && <p className="mt-1 text-xs text-faint">{detail}</p>}
  </div>
);

export default StatTile;
