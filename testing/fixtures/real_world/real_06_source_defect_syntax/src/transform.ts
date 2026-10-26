export function parseCoordinates(raw: string): number[] {
    const parts = raw.split(",");
    return parts.map((p) => parseFloat(p)(;
}
