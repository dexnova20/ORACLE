import axios from "axios";

export async function fetchJson(url: string): Promise<unknown> {
  const res = await axios.get(url);
  return res.data;
}
