// Each mounted account owns one client. Disposing it makes late replies unusable.
function createSessionClient({fetchImpl, storage, onEnd, logoutUrl, timeoutMs = 15000}) {
  let closed = false;
  let writes = Promise.resolve();
  let ending;
  const controllers = new Set();
  const assertActive = () => { if (closed) throw Error("La sesión ya terminó."); };
  const dispose = () => {
    closed = true;
    for (const controller of controllers) controller.abort();
    controllers.clear();
  };
  const store = (key, value) => {
    const operation = writes.catch(() => {}).then(async () => {
      assertActive();
      await storage.setItemAsync(key, value);
      assertActive();
    });
    writes = operation;
    return operation;
  };
  const end = (message, token = "") => {
    if (ending) return ending;
    if (closed) return Promise.resolve();
    dispose();
    ending = (async () => {
      let notice = message;
      if (token) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
          const response = await fetchImpl(logoutUrl, {
            method: "POST", headers: {Authorization: `Bearer ${token}`}, signal: controller.signal,
          });
          if (!response.ok && response.status !== 401) throw Error("logout failed");
        } catch {
          notice = "Saliste de este teléfono, pero no pudimos confirmar el cierre en el servidor. Si perdiste el dispositivo, cambiá tu contraseña.";
        } finally { clearTimeout(timer); }
      }
      await writes.catch(() => {});
      const results = await Promise.allSettled([
        storage.deleteItemAsync("community-token"),
        storage.deleteItemAsync("community-biometric-enabled"),
      ]);
      if (results.some(result => result.status === "rejected")) {
        notice = "La sesión terminó, pero no pudimos borrar el acceso guardado. Volvé a abrir la app para comprobarlo.";
      }
      onEnd(notice);
    })();
    return ending;
  };
  const request = async (url, options = {}) => {
    assertActive();
    const controller = new AbortController();
    controllers.add(controller);
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetchImpl(url, {...options, signal: controller.signal});
      assertActive();
      if (options.headers?.Authorization && response.status === 401) {
        await end("Tu sesión venció o fue cerrada. Volvé a ingresar.");
        throw Error("Tu sesión venció o fue cerrada. Volvé a ingresar.");
      }
      const data = await response.json();
      assertActive();
      return {ok: response.ok, status: response.status, json: async () => { assertActive(); return data; }};
    } finally {
      clearTimeout(timer);
      controllers.delete(controller);
    }
  };
  return {request, store, end, dispose, assertActive};
}

module.exports = {createSessionClient};
