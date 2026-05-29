import { SmartStatusBadge } from "../common/SmartStatusBadge";

export function SmartGridStatusCell({ status, label }: { status?: string | null; label?: string }) {
  return <SmartStatusBadge status={status} label={label} />;
}
