export async function loadPlugin(pluginName: string): Promise<unknown> {
  const mod = await import("./plugins/" + pluginName);
  return mod;
}
