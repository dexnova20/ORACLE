// Intentional undeclared external dependency: axios
import axios from "axios";

export async function fetchRemoteData(endpoint: string): Promise<any> {
    const res = await axios.get(endpoint);
    return res.data;
}
