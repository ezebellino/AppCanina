import {VisitReveal} from "./SuccessMotion";
import ArchiveMotion from "./ArchiveMotion";
import React from "react";
import {Linking, Pressable, StyleSheet, Text, View} from "react-native";

const explanations = {
  received: "El equipo recibió tu interés y lo revisará.",
  contact: "El equipo está conversando con vos sobre la adopción.",
  interview: "Están evaluando si esta adopción es adecuada para ambos.",
  completed: "La adopción quedó concretada.",
  closed: "Esta solicitud terminó sin concretar la adopción.",
};

function Action({title, onPress, disabled}) {
  return <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress}
    style={({pressed}) => [styles.button, (disabled || pressed) && {opacity: 0.6}]}>
    <Text style={styles.buttonText}>{title}</Text>
  </Pressable>;
}

export default function AdoptionActivity({interests, loading, error, pendingId, onRefresh, onRequest, onError, view = "all", counts = {}, onView, onArchive, visitMoment}) {
  const openMap = async address => {
    try {
      await Linking.openURL(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`);
    } catch {
      onError("No pudimos abrir el mapa. Podés copiar la dirección que aparece en la solicitud.");
    }
  };
  return <View style={styles.stack}>
    <Text style={styles.title}>Mis solicitudes de adopción</Text>
    <Text style={styles.help}>Seguí la respuesta del refugio y coordiná una visita para conocer al animal.</Text>
    <Text style={styles.help}>Archivar conserva el historial y solo ordena tu bandeja. Una nueva respuesta vuelve a mostrar la solicitud.</Text>
    <View style={{flexDirection: "row", flexWrap: "wrap", gap: 8}}>
      <Action title={`Mi bandeja (${counts.all ?? 0})${view === "all" ? " · Seleccionada" : ""}`} disabled={loading || pendingId !== null} onPress={() => onView("all")}/>
      <Action title={`Archivadas (${counts.archived ?? 0})${view === "archived" ? " · Seleccionada" : ""}`} disabled={loading || pendingId !== null} onPress={() => onView("archived")}/>
    </View>
    <Action title={loading ? "Actualizando…" : "Actualizar solicitudes"} disabled={loading || pendingId !== null} onPress={onRefresh}/>
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
    {!loading && !error && !interests.length ? <Text style={styles.help}>No hay solicitudes en esta vista.</Text> : null}
    {interests.map(interest => <ArchiveMotion key={interest.id} style={styles.card}>{animate => <>
      <Text style={styles.name}>{interest.animal_name} · {interest.species}</Text>
      {interest.organization_name ? <Text style={styles.help}>{interest.organization_name}</Text> : null}
      <Text style={styles.status}>{interest.status_label}</Text>
      <Text style={styles.help}>{explanations[interest.status] || "Consultá las novedades de tu solicitud."}</Text>
      <Text style={styles.text}>Tu mensaje: {interest.message}</Text>
      {interest.staff_note ? <Text style={styles.text}>Mensaje del equipo: {interest.staff_note}</Text> : null}
      {interest.visit_status && interest.visit_status !== "none" ? <VisitReveal eventKey={interest.visit_status === "accepted" && visitMoment?.interestId === interest.id ? visitMoment.key : null} style={styles.visit}>
        <Text style={styles.status}>{interest.visit_status_label}</Text>
        {interest.visit_status === "requested" ? <Text style={styles.text}>El refugio debe aceptar la visita antes de compartirte la dirección. Usá “Actualizar solicitudes” para consultar su respuesta.</Text> : null}
        {interest.visit_status === "accepted" ? <>
          <Text style={styles.text}>Revisá el día, horario y las indicaciones antes de ir.</Text>
          {interest.visit_address ? <Text selectable style={styles.address}>{interest.visit_address}</Text> : null}
        </> : null}
        {interest.visit_status === "declined" ? <Text style={styles.text}>El refugio no pudo aceptar esta visita.</Text> : null}
        {interest.visit_instructions ? <Text selectable style={styles.text}>{interest.visit_instructions}</Text> : null}
        {interest.visit_status === "accepted" && interest.visit_address ? <Action title="Ver ubicación en Maps" onPress={() => openMap(interest.visit_address)}/> : null}
      </VisitReveal> : null}
      {interest.can_request_visit ? <Action title={pendingId === interest.id ? "Enviando solicitud…" : "Coordinar visita"}
        disabled={pendingId !== null || loading} onPress={() => onRequest(interest.id)}/> : null}
      {interest.can_archive || interest.is_archived ? <Action title={interest.is_archived ? "Restaurar en mi bandeja" : "Archivar solicitud"}
        disabled={pendingId !== null || loading} onPress={() => onArchive(interest, animate)}/> : null}
    </>}</ArchiveMotion>)}
  </View>;
}

const styles = StyleSheet.create({
  stack: {gap: 14}, title: {fontSize: 24, fontWeight: "800", color: "#153c36"},
  card: {backgroundColor: "#fff", borderRadius: 20, padding: 20, gap: 10, borderWidth: 1, borderColor: "#d7e6e2"},
  name: {fontSize: 20, fontWeight: "800", color: "#153c36"},
  status: {fontWeight: "700", fontSize: 16, color: "#145c4c"},
  help: {color: "#526660", lineHeight: 22}, text: {color: "#263f38", lineHeight: 22},
  address: {fontWeight: "700", color: "#153c36", lineHeight: 24},
  visit: {backgroundColor: "#edf7f2", padding: 16, borderRadius: 14, gap: 10},
  button: {alignSelf: "flex-start", backgroundColor: "#176b55", borderRadius: 12, paddingHorizontal: 18, paddingVertical: 14},
  buttonText: {color: "#fff", fontWeight: "700", fontSize: 15}, error: {color: "#a12727", lineHeight: 22},
});
