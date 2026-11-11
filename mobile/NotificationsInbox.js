import React, {useEffect, useRef, useState} from "react";
import {Pressable, StyleSheet, Text, View} from "react-native";

function Action({title, onPress, disabled}) {
  return <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress}
    style={({pressed}) => [styles.button, (pressed || disabled) && {opacity: 0.5}]}><Text style={styles.buttonText}>{title}</Text></Pressable>;
}

export default function NotificationsInbox({api, token, sessionRequest, onCount, onOpen}) {
  const [data, setData] = useState({notifications: [], has_next: false});
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const operation = useRef({id: 0, busy: false});
  const load = async (nextFilter = filter, nextPage = page) => {
    if (operation.current.busy) return;
    const id = ++operation.current.id;
    operation.current.busy = true; setBusy(true); setError("");
    try {
      const response = await sessionRequest(`${api}/novedades/?filter=${nextFilter}&page=${nextPage}`, {headers: {Authorization: `Bearer ${token}`}});
      const result = await response.json();
      if (operation.current.id !== id) return;
      if (!response.ok) throw Error(result.detail || "No pudimos cargar las notificaciones.");
      setData(result); setPage(nextPage); setFilter(nextFilter); onCount(result.unread_count);
    } catch (err) { if (operation.current.id === id) setError(err.message || "Revisá tu conexión y volvé a intentar."); }
    finally { if (operation.current.id === id) { operation.current.busy = false; setBusy(false); } }
  };
  useEffect(() => { load(); return () => { operation.current.id++; operation.current.busy = false; }; }, []);
  const open = async item => {
    if (operation.current.busy) return;
    const id = ++operation.current.id;
    operation.current.busy = true; setBusy(true); setError("");
    try { await onOpen(item, () => operation.current.id === id); }
    catch (err) { if (operation.current.id === id) setError(err.message || "No pudimos abrir esta novedad. Sigue pendiente."); }
    finally { if (operation.current.id === id) { operation.current.busy = false; setBusy(false); } }
  };
  return <View style={styles.stack}>
    <Text style={styles.title}>Notificaciones</Text>
    <Text style={styles.help}>Búsquedas, visitas y solicitudes de adopción. Se marcan como leídas al abrir su contenido.</Text>
    <View style={styles.row}>
      <Action title={filter === "all" ? "✓ Todas" : "Todas"} disabled={busy} onPress={() => load("all", 1)}/>
      <Action title={filter === "unread" ? "✓ Sin leer" : "Sin leer"} disabled={busy} onPress={() => load("unread", 1)}/>
      <Action title={busy ? "Cargando…" : "Actualizar"} disabled={busy} onPress={() => load()}/>
    </View>
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    {!busy && !error && !data.notifications.length ? <Text style={styles.help}>{filter === "unread" ? "No tenés novedades sin leer en esta página." : "No hay notificaciones en esta página."}</Text> : null}
    {data.notifications.map(item => <View key={item.key} style={[styles.card, item.unread && styles.unread]}>
      <Text style={styles.category}>{item.category} · {item.unread ? "Sin leer" : "Leída"}</Text>
      <Text style={styles.name}>{item.title}</Text><Text style={styles.text}>{item.body}</Text>
      <Text style={styles.help}>{new Date(item.activity_at).toLocaleString()}</Text>
      <Action title="Ver novedad" disabled={busy} onPress={() => open(item)}/>
    </View>)}
    <View style={styles.row}>
      {page > 1 ? <Action title="Anterior" disabled={busy} onPress={() => load(filter, page - 1)}/> : null}
      <Text style={styles.help}>Página {page}</Text>
      {data.has_next ? <Action title="Siguiente" disabled={busy} onPress={() => load(filter, page + 1)}/> : null}
    </View>
  </View>;
}
const styles = StyleSheet.create({
  stack: {gap: 14}, row: {flexDirection: "row", flexWrap: "wrap", gap: 8, alignItems: "center"},
  title: {fontSize: 24, fontWeight: "800", color: "#153c36"}, name: {fontSize: 18, fontWeight: "700", color: "#153c36"},
  category: {fontWeight: "700", color: "#176b55"}, text: {color: "#263f38", lineHeight: 22}, help: {color: "#526660", lineHeight: 22},
  card: {padding: 18, borderWidth: 1, borderColor: "#d7e6e2", borderRadius: 16, gap: 10, backgroundColor: "#fff"},
  unread: {borderLeftWidth: 5, borderLeftColor: "#176b55", backgroundColor: "#eef9f3"},
  button: {alignSelf: "flex-start", padding: 12, borderRadius: 12, backgroundColor: "#176b55"},
  buttonText: {color: "#fff", fontWeight: "700"}, error: {color: "#a12727", lineHeight: 22},
});
