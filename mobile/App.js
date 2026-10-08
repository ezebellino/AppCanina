import React, {useState} from "react";
import {Button, Image, Platform, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View} from "react-native";
import * as SecureStore from "expo-secure-store";
import * as Location from "expo-location";
import * as ImagePicker from "expo-image-picker";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";

const API = process.env.EXPO_PUBLIC_API_URL || "https://appcanina-production.up.railway.app/extraviados/api/v1";

Notifications.setNotificationHandler({
  handleNotification: async () => ({shouldShowAlert: true, shouldPlaySound: true, shouldSetBadge: true}),
});

export default function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [email, setEmail] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("Ingresá para colaborar.");
  const [photoUri, setPhotoUri] = useState("");
  const [notifications, setNotifications] = useState([]);
  const [screen, setScreen] = useState("panel");
  const [reportState, setReportState] = useState("activos");
  const [reports, setReports] = useState([]);
  const [reportQuery, setReportQuery] = useState("");
  const [requestName, setRequestName] = useState("");
  const [requestSpecies, setRequestSpecies] = useState("");
  const [requestBreed, setRequestBreed] = useState("");
  const [requestArea, setRequestArea] = useState("");
  const [requestDescription, setRequestDescription] = useState("");
  const [requestPhoto, setRequestPhoto] = useState(null);
  const [myRequests, setMyRequests] = useState([]);
  const [editingRequest, setEditingRequest] = useState(null);

  const loadNotifications = async (accessToken = token) => {
    const response = await fetch(`${API}/notificaciones/`, {headers: {Authorization: `Bearer ${accessToken}`}});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail || "No se pudieron consultar las notificaciones.");
    setNotifications(data.notifications);
    setMessage(data.notifications.length ? `${data.notifications.length} notificación${data.notifications.length === 1 ? "" : "es"} pendiente${data.notifications.length === 1 ? "" : "s"}.` : "No hay notificaciones pendientes.");
  };

  const loadReports = async (accessToken = token, state = reportState, query = reportQuery) => {
    try {
      const params = new URLSearchParams({estado: state});
      if (query.trim()) params.set("q", query.trim());
      const response = await fetch(`${API}/avisos/?${params.toString()}`, {headers: {Authorization: `Bearer ${accessToken}`}});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudieron cargar los avisos.");
      setReports(data.reports);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const activatePushNotifications = async () => {
    if (!Device.isDevice) {
      setMessage("Las alertas push requieren un teléfono físico.");
      return;
    }
    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("animales-extraviados", {
        name: "Animales extraviados",
        importance: Notifications.AndroidImportance.HIGH,
        vibrationPattern: [0, 250, 200, 250],
      });
    }
    const current = await Notifications.getPermissionsAsync();
    const permission = current.status === "granted" ? current : await Notifications.requestPermissionsAsync();
    if (permission.status !== "granted") {
      setMessage("No autorizaste las alertas. Podés activarlas más adelante desde la configuración del teléfono.");
      return;
    }
    const projectId = Constants.easConfig?.projectId || Constants.expoConfig?.extra?.eas?.projectId || process.env.EXPO_PUBLIC_EAS_PROJECT_ID;
    if (!projectId) {
      setMessage("Falta asociar el proyecto de notificaciones antes de activar alertas en este dispositivo.");
      return;
    }
    try {
      const pushToken = (await Notifications.getExpoPushTokenAsync({projectId})).data;
      const response = await fetch(`${API}/dispositivos/push/`, {
        method: "POST",
        headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`},
        body: JSON.stringify({push_token: pushToken, platform: Platform.OS}),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo registrar este dispositivo.");
      setMessage("Alertas activadas en este teléfono.");
    } catch (error) {
      setMessage(error.message);
    }
  };

  const login = async () => {
    try {
      const response = await fetch(`${API}/sesion/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password, device_name: "App móvil"}),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo iniciar sesión.");
      await SecureStore.setItemAsync("community-token", data.token);
      setToken(data.token);
      setMessage(`Sesión iniciada: ${data.user.username}`);
      await loadReports(data.token);
      await loadNotifications(data.token);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const register = async () => {
    try {
      const response = await fetch(`${API}/registro/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          username,
          first_name: firstName,
          email,
          password,
          password_confirmation: passwordConfirmation,
          device_name: "App móvil",
        }),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo crear la cuenta.");
      await SecureStore.setItemAsync("community-token", data.token);
      setToken(data.token);
      setMessage(`Cuenta creada. ¡Gracias por colaborar, ${data.user.username}!`);
      await loadReports(data.token);
      await loadNotifications(data.token);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const shareLocation = async () => {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") {
      setMessage("No compartiste la ubicación. Podrás indicar la zona manualmente.");
      return;
    }
    const location = await Location.getCurrentPositionAsync({accuracy: Location.Accuracy.Balanced});
    setMessage(`Ubicación obtenida: ${location.coords.latitude.toFixed(4)}, ${location.coords.longitude.toFixed(4)}. Al publicar, el mapa mostrará una zona aproximada.`);
  };

  const takePhoto = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      setMessage("No autorizaste la cámara. Podés continuar sin foto.");
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.75,
    });
    if (!result.canceled) {
      setPhotoUri(result.assets[0].uri);
      setMessage("Foto lista para adjuntar al próximo aviso o avistamiento.");
    }
  };

  const chooseRequestPhoto = async (fromCamera = false) => {
    const permission = fromCamera
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setMessage(fromCamera ? "No autorizaste la cámara. Podés elegir una foto de tu galería." : "No autorizaste el acceso a tus fotos. Podés usar la cámara.");
      return;
    }
    const result = fromCamera
      ? await ImagePicker.launchCameraAsync({mediaTypes: ImagePicker.MediaTypeOptions.Images, allowsEditing: true, quality: 0.8})
      : await ImagePicker.launchImageLibraryAsync({mediaTypes: ImagePicker.MediaTypeOptions.Images, allowsEditing: true, quality: 0.8});
    if (!result.canceled) {
      setRequestPhoto(result.assets[0]);
      setMessage("Foto del animal lista para enviar con la solicitud.");
    }
  };

  const loadMySearchRequests = async (accessToken = token) => {
    try {
      const response = await fetch(`${API}/solicitudes-busqueda/mias/`, {headers: {Authorization: `Bearer ${accessToken}`}});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudieron cargar tus solicitudes.");
      setMyRequests(data.requests);
    } catch (error) {
      setMessage(error.message);
    }
  };

  const resetSearchRequest = () => {
    setEditingRequest(null); setRequestName(""); setRequestSpecies(""); setRequestBreed("");
    setRequestArea(""); setRequestDescription(""); setRequestPhoto(null);
  };

  const editSearchRequest = (request) => {
    setEditingRequest(request);
    setRequestName(request.name || ""); setRequestSpecies(request.species || "");
    setRequestBreed(request.breed || ""); setRequestArea(request.area || "");
    setRequestDescription(request.description || ""); setRequestPhoto(null);
    setScreen("solicitud");
  };

  const submitSearchRequest = async () => {
    try {
      const form = new FormData();
      form.append("name", requestName); form.append("species", requestSpecies); form.append("breed", requestBreed);
      form.append("area", requestArea); form.append("description", requestDescription);
      if (requestPhoto?.uri) {
        form.append("photo", {uri: requestPhoto.uri, name: requestPhoto.fileName || "animal.jpg", type: requestPhoto.mimeType || "image/jpeg"});
      }
      const response = await fetch(`${API}/solicitudes-busqueda/${editingRequest ? `${editingRequest.id}/editar/` : ""}`, {
        method: "POST",
        headers: {Authorization: `Bearer ${token}`},
        body: form,
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo enviar la solicitud.");
      resetSearchRequest();
      setScreen("panel");
      setMessage(data.detail);
      await loadMySearchRequests();
    } catch (error) {
      setMessage(error.message);
    }
  };

  const changeReportState = async (state) => {
    setReportState(state);
    await loadReports(token, state, reportQuery);
  };

  return <SafeAreaView style={styles.screen}>
    <ScrollView contentContainerStyle={styles.content}>
      <Text style={styles.title}>Tu Veterinaria</Text>
      <Text style={styles.subtitle}>Comunidad · animales extraviados</Text>
      {!token ? <View style={styles.stack}>
      {isRegistering ? <Text style={styles.help}>Creá tu cuenta para recibir alertas y compartir avistamientos. Tu acceso será solo comunitario.</Text> : null}
      {isRegistering ? <View style={styles.field}><Text style={styles.fieldLabel}>Nombre <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="Ej.: Sofía" placeholderTextColor="#6c8378" value={firstName} onChangeText={setFirstName} style={styles.input}/></View> : null}
      <View style={styles.field}><Text style={styles.fieldLabel}>Usuario</Text><TextInput placeholder="Elegí un usuario" placeholderTextColor="#6c8378" value={username} onChangeText={setUsername} autoCapitalize="none" style={styles.input}/></View>
      {isRegistering ? <View style={styles.field}><Text style={styles.fieldLabel}>Correo electrónico <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="nombre@correo.com" placeholderTextColor="#6c8378" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" style={styles.input}/></View> : null}
      <View style={styles.field}><Text style={styles.fieldLabel}>Contraseña</Text><TextInput placeholder="Mínimo 8 caracteres" placeholderTextColor="#6c8378" value={password} onChangeText={setPassword} secureTextEntry style={styles.input}/></View>
      {isRegistering ? <View style={styles.field}><Text style={styles.fieldLabel}>Repetir contraseña</Text><TextInput placeholder="Repetí tu contraseña" placeholderTextColor="#6c8378" value={passwordConfirmation} onChangeText={setPasswordConfirmation} secureTextEntry style={styles.input}/></View> : null}
      <Button title={isRegistering ? "Crear cuenta" : "Ingresar"} onPress={isRegistering ? register : login}/>
      <Button title={isRegistering ? "Ya tengo una cuenta" : "Crear una cuenta para colaborar"} onPress={() => { setIsRegistering(!isRegistering); setMessage(isRegistering ? "Ingresá para colaborar." : "Completá tus datos para crear una cuenta."); }}/>
    </View> : <View style={styles.stack}>
      <View style={styles.nav}>
        <Button title="Panel" onPress={() => setScreen("panel")}/>
        <Button title="Buscar" onPress={() => setScreen("buscar")}/>
        <Button title="Pedir búsqueda" onPress={() => { resetSearchRequest(); setScreen("solicitud"); }}/>
        <Button title="Mis solicitudes" onPress={() => { setScreen("mis-solicitudes"); loadMySearchRequests(); }}/>
      </View>
      {screen === "panel" ? <View style={styles.stack}>
        <Text style={styles.sectionTitle}>Animales que necesitan ayuda</Text>
        <View style={styles.nav}><Button title="Se buscan" onPress={() => changeReportState("activos")}/><Button title="Encontrados" onPress={() => changeReportState("encontrados")}/></View>
        <Button title="Actualizar panel" onPress={() => loadReports()}/>
        {reports.length ? reports.map(report => <View key={report.id} style={styles.reportCard}>
          {report.photo_url ? <Image source={{uri: report.photo_url}} style={styles.reportPhoto}/> : <View style={styles.reportPhotoPlaceholder}><Text style={styles.reportPhotoIcon}>{report.species?.toLowerCase().includes("gato") ? "🐱" : report.species?.toLowerCase().includes("perro") ? "🐶" : "🐾"}</Text><Text style={styles.reportPhotoCaption}>Sin foto disponible</Text></View>}
          <View style={styles.reportContent}><Text style={styles.notificationTitle}>{report.name} · {report.species}</Text><Text style={styles.notificationArea}>⌖ {report.area}</Text><Text style={styles.reportMeta}>{report.status === "resolved" ? "Encontrado" : "Se busca"}</Text><Text>{report.description || "Sin señas particulares cargadas."}</Text></View>
        </View>) : <Text style={styles.empty}>No hay avisos en esta sección por ahora.</Text>}
      </View> : null}
      {screen === "buscar" ? <View style={styles.stack}>
        <Text style={styles.sectionTitle}>Buscar un animal</Text>
        <View style={styles.field}><Text style={styles.fieldLabel}>Nombre</Text><TextInput placeholder="Ej.: Luna" placeholderTextColor="#6c8378" value={reportQuery} onChangeText={setReportQuery} style={styles.input}/></View>
        <Button title="Buscar entre los avisos" onPress={() => loadReports(token, reportState, reportQuery)}/>
        {reports.map(report => <View key={report.id} style={styles.reportCard}>{report.photo_url ? <Image source={{uri: report.photo_url}} style={styles.reportPhoto}/> : <View style={styles.reportPhotoPlaceholder}><Text style={styles.reportPhotoIcon}>🐾</Text></View>}<View style={styles.reportContent}><Text style={styles.notificationTitle}>{report.name} · {report.species}</Text><Text style={styles.notificationArea}>⌖ {report.area}</Text></View></View>)}
      </View> : null}
      {screen === "solicitud" ? <View style={styles.stack}>
        <Text style={styles.sectionTitle}>{editingRequest ? "Editar solicitud" : "Solicitar una búsqueda"}</Text>
        <Text style={styles.help}>{editingRequest ? "Corregí los datos y el equipo la revisará nuevamente." : "Una foto clara ayuda mucho a reconocerlo en la calle. El equipo revisará la solicitud antes de hacerla pública."}</Text>
        <View style={styles.requestPhotoBox}>{requestPhoto?.uri ? <Image source={{uri: requestPhoto.uri}} style={styles.requestPhoto}/> : editingRequest?.photo_url ? <Image source={{uri: editingRequest.photo_url}} style={styles.requestPhoto}/> : <View style={styles.requestPhotoEmpty}><Text style={styles.reportPhotoIcon}>🐾</Text><Text style={styles.help}>Sumá una foto clara del animal</Text></View>}</View>
        <View style={styles.nav}><Button title="Usar cámara" onPress={() => chooseRequestPhoto(true)}/><Button title="Elegir de galería" onPress={() => chooseRequestPhoto(false)}/>{requestPhoto ? <Button title="Quitar foto nueva" onPress={() => setRequestPhoto(null)}/> : null}</View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Nombre del animal</Text><TextInput placeholder="Ej.: Nube" placeholderTextColor="#6c8378" value={requestName} onChangeText={setRequestName} style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Especie</Text><TextInput placeholder="Perro, gato u otro" placeholderTextColor="#6c8378" value={requestSpecies} onChangeText={setRequestSpecies} style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Raza <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="Ej.: Mestizo" placeholderTextColor="#6c8378" value={requestBreed} onChangeText={setRequestBreed} style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Zona aproximada</Text><TextInput placeholder="Ej.: Barrio Norte" placeholderTextColor="#6c8378" value={requestArea} onChangeText={setRequestArea} style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Señas particulares <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="Collar, color, tamaño..." placeholderTextColor="#6c8378" value={requestDescription} onChangeText={setRequestDescription} multiline style={[styles.input, styles.textarea]}/></View>
        <Button title={editingRequest ? "Guardar cambios" : "Enviar solicitud"} onPress={submitSearchRequest}/>
        {editingRequest ? <Button title="Cancelar edición" onPress={() => { resetSearchRequest(); setScreen("mis-solicitudes"); loadMySearchRequests(); }}/> : null}
      </View> : null}
      {screen === "mis-solicitudes" ? <View style={styles.stack}>
        <Text style={styles.sectionTitle}>Mis solicitudes</Text>
        <Text style={styles.help}>Podés editar una solicitud mientras está en revisión o si el equipo te pidió una corrección.</Text>
        {myRequests.length ? myRequests.map(request => <View key={request.id} style={styles.reportCard}>
          {request.photo_url ? <Image source={{uri: request.photo_url}} style={styles.reportPhoto}/> : <View style={styles.reportPhotoPlaceholder}><Text style={styles.reportPhotoIcon}>🐾</Text><Text style={styles.reportPhotoCaption}>Sin foto</Text></View>}
          <View style={styles.reportContent}><Text style={styles.notificationTitle}>{request.name} · {request.species}</Text><Text style={styles.reportMeta}>{request.status_label}</Text><Text style={styles.notificationArea}>⌖ {request.area}</Text>{request.review_note ? <Text style={styles.reviewNote}>Nota del equipo: {request.review_note}</Text> : null}{request.editable ? <Button title="Editar solicitud" onPress={() => editSearchRequest(request)}/> : <Text style={styles.help}>Esta solicitud ya está publicada o cerrada.</Text>}</View>
        </View>) : <Text style={styles.empty}>Todavía no enviaste solicitudes.</Text>}
      </View> : null}
      <View style={styles.divider}/>
      <Text style={styles.sectionTitle}>Mi teléfono</Text>
      <Button title="⌖ Compartir mi ubicación" onPress={shareLocation}/>
      <Button title="▣ Usar cámara" onPress={takePhoto}/>
      <Button title="🔔 Activar alertas" onPress={activatePushNotifications}/>
      <Button title="Ver mis notificaciones" onPress={() => loadNotifications()}/>
      {photoUri ? <Image source={{uri: photoUri}} style={styles.preview}/> : null}
      {notifications.slice(0, 5).map(notification => <View key={notification.id} style={styles.notificationCard}>
        {notification.photo_url ? <Image source={{uri: notification.photo_url}} style={styles.notificationPhoto}/> : null}
        <View style={styles.notificationContent}><Text style={styles.notificationTitle}>{notification.title}</Text><Text style={styles.notificationAnimal}>{notification.animal_name} · {notification.species}</Text><Text style={styles.notificationArea}>⌖ {notification.area}</Text><Text>{notification.description || notification.body}</Text></View>
      </View>)}
    </View>}
      <Text style={styles.message}>{message}</Text>
    </ScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  screen: {flex: 1, backgroundColor: "#f7faf8"},
  content: {padding: 24, gap: 12},
  title: {fontSize: 26, fontWeight: "700", color: "#1d4334"},
  subtitle: {color: "#557267"},
  stack: {gap: 12},
  field: {gap: 6},
  fieldLabel: {color: "#1d4334", fontSize: 15, fontWeight: "700"},
  optional: {color: "#557267", fontWeight: "400"},
  input: {borderWidth: 1, borderColor: "#cbd9d1", backgroundColor: "#fff", color: "#172d24", borderRadius: 10, padding: 12},
  textarea: {minHeight: 90, textAlignVertical: "top"},
  help: {lineHeight: 20, color: "#466156"},
  sectionTitle: {fontSize: 19, fontWeight: "700", color: "#1d4334", marginTop: 6},
  nav: {flexDirection: "row", flexWrap: "wrap", gap: 8},
  divider: {height: 1, backgroundColor: "#dbe7df", marginVertical: 8},
  empty: {color: "#557267", fontStyle: "italic", paddingVertical: 12},
  message: {lineHeight: 21, color: "#213a30"},
  preview: {width: "100%", height: 220, borderRadius: 12, resizeMode: "cover"},
  notificationCard: {backgroundColor: "#fff", borderWidth: 1, borderColor: "#dbe7df", borderRadius: 14, overflow: "hidden"},
  notificationPhoto: {width: "100%", height: 180, resizeMode: "cover"},
  notificationContent: {padding: 14, gap: 4},
  notificationTitle: {fontSize: 17, fontWeight: "700", color: "#1d4334"},
  notificationAnimal: {fontWeight: "600", color: "#355f4a"},
  notificationArea: {color: "#557267"},
  reportCard: {backgroundColor: "#fff", borderWidth: 1, borderColor: "#dbe7df", borderRadius: 14, overflow: "hidden"},
  reportPhoto: {width: "100%", height: 250, resizeMode: "cover"},
  reportPhotoPlaceholder: {width: "100%", height: 250, alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: "#eaf2ed"},
  reportPhotoIcon: {fontSize: 52},
  reportPhotoCaption: {color: "#557267"},
  reportContent: {padding: 14, gap: 4},
  reportMeta: {color: "#147d59", fontWeight: "700"},
  requestPhotoBox: {borderRadius: 14, overflow: "hidden", borderWidth: 1, borderColor: "#cbd9d1", backgroundColor: "#fff"},
  requestPhoto: {width: "100%", height: 280, resizeMode: "cover"},
  requestPhotoEmpty: {height: 180, alignItems: "center", justifyContent: "center", gap: 6, padding: 18},
  reviewNote: {color: "#78481e", backgroundColor: "#fff4df", padding: 10, borderRadius: 8},
});
