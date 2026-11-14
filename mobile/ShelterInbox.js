import ArchiveMotion from "./ArchiveMotion";
import React, {useEffect, useRef, useState} from "react";
import {Pressable, StyleSheet, Text, TextInput, View} from "react-native";

function Action({title, onPress, disabled, selected}) {
  return <Pressable accessibilityRole="button" accessibilityState={{disabled, selected}} disabled={disabled}
    onPress={onPress} style={({pressed}) => [styles.button, selected && styles.selected, (pressed || disabled) && {opacity: 0.55}]}>
    <Text style={styles.buttonText}>{title}</Text>
  </Pressable>;
}

function RequestCard({item, choices, disabled, onSave}) {
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState(item.status);
  const [note, setNote] = useState(item.staff_note || "");
  const [address, setAddress] = useState(item.visit_address || "");
  const [instructions, setInstructions] = useState(item.visit_instructions || "");
  return <ArchiveMotion style={styles.card}>{animate => <>
    <Text style={styles.name}>{item.animal_name} · {item.organization_name}</Text>
    <Text style={styles.label}>{item.applicant_name}</Text>
    <Text style={styles.text}>{item.message}</Text>
    <Text style={styles.label}>{item.status_label} · {item.visit_status_label}</Text>
    {item.staff_note ? <Text style={styles.text}>Mensaje enviado: {item.staff_note}</Text> : null}
    {item.visit_address ? <Text selectable style={styles.text}>{item.visit_address}</Text> : null}
    {item.visit_instructions ? <Text style={styles.text}>{item.visit_instructions}</Text> : null}
    {item.can_archive || item.is_archived ? <Action title={item.is_archived ? "Restaurar en mi bandeja" : "Archivar solicitud"} disabled={disabled}
      onPress={() => onSave(item, {action: item.is_archived ? "restore" : "archive"}, animate)}/> : null}
    <Action title={editing ? "Cerrar edición" : "Gestionar solicitud"} disabled={disabled} onPress={() => setEditing(!editing)}/>
    {editing ? <View style={styles.stack}>
      <Text style={styles.label}>Estado de la solicitud</Text>
      <View style={styles.row}>{choices.map(choice => <Action key={choice.value} title={choice.label}
        selected={status === choice.value} disabled={disabled} onPress={() => setStatus(choice.value)}/>)}</View>
      <Text style={styles.help}>Recibido: pendiente de revisión. En conversación: contacto iniciado. En evaluación: adopción en revisión. Adopción concretada: proceso completado. No continuó: solicitud cerrada.</Text>
      <Text style={styles.label}>Mensaje visible para la persona</Text>
      <TextInput accessibilityLabel="Mensaje visible para la persona" editable={!disabled} multiline maxLength={280}
        value={note} onChangeText={setNote} style={styles.input}/>
      <Text style={styles.help}>Este estado corresponde a la solicitud; no cambia la publicación del animal.</Text>
      <Action title="Guardar estado y mensaje" disabled={disabled} onPress={() => onSave(item, {action: "status", status, staff_note: note})}/>
      {item.can_decline_visit ? <View style={styles.visit}>
        <Text style={styles.name}>Responder visita</Text>
        <Text style={styles.label}>Dirección completa, con ciudad</Text>
        <TextInput accessibilityLabel="Dirección de la visita" editable={!disabled} maxLength={300} value={address}
          onChangeText={setAddress} placeholder="Calle, número y ciudad" placeholderTextColor="#62786f" style={styles.input}/>
        <Text style={styles.label}>Día, horario e indicaciones</Text>
        <TextInput accessibilityLabel="Día, horario e indicaciones" editable={!disabled} multiline maxLength={280}
          value={instructions} onChangeText={setInstructions} style={styles.input}/>
        <Text style={styles.help}>La dirección se comparte con esta persona únicamente al aceptar. Las indicaciones también se muestran si rechazás la visita.</Text>
        {item.can_accept_visit ? <Action title="Aceptar visita y compartir ubicación" disabled={disabled || !address.trim()}
          onPress={() => onSave(item, {action: "accept", visit_address: address, visit_instructions: instructions})}/> : null}
        <Action title="No puedo aceptar esta visita" disabled={disabled}
          onPress={() => onSave(item, {action: "decline", visit_instructions: instructions})}/>
      </View> : null}
    </View> : null}
  </>}</ArchiveMotion>;
}

export default function ShelterInbox({api, token, sessionRequest, initialData}) {
  const [data, setData] = useState(initialData || {interests: [], counts: {}, status_choices: [], has_next: false});
  const [view, setView] = useState("all");
  const [focused, setFocused] = useState(Boolean(initialData));
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const operation = useRef({id: 0, busy: false});

  const load = async (nextView = view, nextPage = page) => {
    if (operation.current.busy) return;
    const id = ++operation.current.id;
    operation.current.busy = true; setBusy(true); setError("");
    try {
      const response = await sessionRequest(`${api}/adopciones/bandeja/?view=${nextView}&page=${nextPage}`, {headers: {Authorization: `Bearer ${token}`}});
      const result = await response.json();
      if (operation.current.id !== id) return;
      if (!response.ok) {
        if ([403, 404].includes(response.status)) setData({interests: [], counts: {}, status_choices: []});
        throw Error(result.detail || "No pudimos cargar la bandeja.");
      }
      setData(result); setFocused(false); setView(nextView); setPage(nextPage); setNeedsRefresh(false);
    } catch (err) {
      if (operation.current.id === id) { setError(err.message || "Revisá tu conexión y volvé a intentar."); setNeedsRefresh(true); }
    } finally {
      if (operation.current.id === id) { operation.current.busy = false; setBusy(false); }
    }
  };
  useEffect(() => {
    if (!initialData) load("all", 1);
    return () => { operation.current.id++; operation.current.busy = false; };
  }, []);

  const save = async (item, changes, animate) => {
    if (operation.current.busy || needsRefresh) return;
    const id = ++operation.current.id;
    operation.current.busy = true; setBusy(true); setError(""); setNotice("");
    try {
      const archiving = ["archive", "restore"].includes(changes.action);
      const route = archiving ? `archivo/institution/${item.id}` : `bandeja/${item.id}`;
      const response = await sessionRequest(`${api}/adopciones/${route}/`, {
        method: "POST", headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"},
        body: JSON.stringify({...changes, expected_updated_at: item.updated_at}),
      });
      const result = await response.json();
      if (operation.current.id !== id) return;
      if (!response.ok) {
        if ([403, 404].includes(response.status)) setData({interests: [], counts: {}, status_choices: []});
        throw Error(result.detail || "No pudimos guardar. Actualizá para comprobar el resultado.");
      }
      if (changes.action === "archive") await animate?.();
      if (operation.current.id !== id) return;
      setNotice(result.detail);
      setData(current => ({...current, interests: archiving ? current.interests.filter(existing => existing.id !== item.id) : current.interests.map(existing => existing.id === item.id ? result.interest : existing)}));
      operation.current.busy = false;
      await load(view, page);
    } catch (err) {
      if (operation.current.id === id) { setError(err.message || "Actualizá la bandeja para comprobar si se guardó."); setNeedsRefresh(true); }
    } finally {
      if (operation.current.id === id) { operation.current.busy = false; setBusy(false); }
    }
  };

  return <View style={styles.stack}>
    <Text style={styles.title}>Solicitudes recibidas</Text>
    <Text style={styles.help}>Administrá las adopciones de tus refugios. Archivar solo ordena tu bandeja y conserva el historial.</Text>
    {focused ? <Text style={styles.help}>Solicitud abierta desde una notificación. Actualizá la bandeja para ver todas.</Text> : <View style={styles.row}>{[["all", "Mi bandeja"], ["received", "Nuevas"], ["visits", "Visitas pendientes"], ["archived", "Archivadas"]].map(([value, label]) =>
      <Action key={value} title={`${label} (${data.counts[value] ?? 0})`} selected={view === value} disabled={busy} onPress={() => load(value, 1)}/>)}</View>}
    <Action title={busy ? "Cargando…" : "Actualizar bandeja"} disabled={busy} onPress={() => load()}/>
    {notice ? <Text accessibilityLiveRegion="polite" style={styles.text}>{notice}</Text> : null}
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    {!busy && !error && !data.interests.length ? <Text style={styles.help}>No hay solicitudes en esta página con el filtro elegido.</Text> : null}
    {data.interests.map(item => <RequestCard key={`${item.id}:${item.updated_at}`} item={item} choices={data.status_choices}
      disabled={busy || needsRefresh} onSave={save}/>)}
    <View style={styles.row}>
      {page > 1 ? <Action title="Anterior" disabled={busy} onPress={() => load(view, page - 1)}/> : null}
      <Text style={styles.help}>Página {page}</Text>
      {data.has_next ? <Action title="Siguiente" disabled={busy} onPress={() => load(view, page + 1)}/> : null}
    </View>
  </View>;
}

const styles = StyleSheet.create({
  stack: {gap: 14}, row: {flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: 8},
  title: {fontSize: 24, color: "#153c36", fontWeight: "800"}, name: {fontSize: 18, color: "#153c36", fontWeight: "700"},
  card: {padding: 18, backgroundColor: "#fff", borderRadius: 18, gap: 12, borderWidth: 1, borderColor: "#d7e6e2"},
  label: {fontWeight: "700", color: "#1d5143"}, text: {color: "#263f38", lineHeight: 22}, help: {color: "#526660", lineHeight: 22},
  input: {borderWidth: 1, borderColor: "#a4bdb3", borderRadius: 10, padding: 12, color: "#153c36", backgroundColor: "#fff", minHeight: 48},
  visit: {padding: 14, backgroundColor: "#edf7f2", borderRadius: 12, gap: 12}, error: {color: "#a12727", lineHeight: 22},
  button: {alignSelf: "flex-start", backgroundColor: "#176b55", borderRadius: 12, padding: 12, borderWidth: 2, borderColor: "transparent"},
  selected: {backgroundColor: "#104936", borderColor: "#b4e8cf"}, buttonText: {color: "#fff", fontWeight: "700"},
});
