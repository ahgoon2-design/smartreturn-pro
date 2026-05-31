import { apiRequest } from "./client";
import type { ClientDetail, ClientSummary } from "../types/master";

export async function listClients() {
  const data = await apiRequest<ClientSummary[] | { items?: ClientSummary[] }>("/api/master/clients");
  return Array.isArray(data) ? data : data.items || [];
}

export async function getClient(clientId: number) {
  return apiRequest<ClientDetail | null>(`/api/master/clients/${clientId}`);
}
