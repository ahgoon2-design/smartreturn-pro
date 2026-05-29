import { apiRequest } from "./client";
import type { ClientSummary } from "../types/master";

export async function listClients() {
  const data = await apiRequest<ClientSummary[] | { items?: ClientSummary[] }>("/api/master/clients");
  return Array.isArray(data) ? data : data.items || [];
}
