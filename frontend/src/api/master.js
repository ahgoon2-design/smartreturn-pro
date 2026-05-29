import { apiRequest } from "../lib/apiClient.js";

export async function listClients() {
  const result = await apiRequest("/api/master/clients");
  return result.data || [];
}
