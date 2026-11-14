import ShelterDonation from "./ShelterDonation";
import React, {useEffect, useRef, useState} from "react";
import {AppState, Image, Modal, Platform, Pressable, ScrollView, Share, StyleSheet, Text, TextInput, View} from "react-native";
import {SafeAreaProvider, SafeAreaView} from "react-native-safe-area-context";
import * as Clipboard from "expo-clipboard";
import * as SecureStore from "expo-secure-store";
import * as Location from "expo-location";
import * as ImagePicker from "expo-image-picker";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import Constants from "expo-constants";
import * as LocalAuthentication from "expo-local-authentication";
import {createSessionClient} from "./session-client.cjs";
import SearchMap from "./SearchMap";
import AdoptionActivity from "./AdoptionActivity";
import ShelterInbox from "./ShelterInbox";
import NotificationsInbox from "./NotificationsInbox";

const API = process.env.EXPO_PUBLIC_API_URL || "https://lazuna.up.railway.app/extraviados/api/v1";

Notifications.setNotificationHandler({
  handleNotification: async () => ({shouldShowBanner: true, shouldShowList: true, shouldPlaySound: true, shouldSetBadge: true}),
});

function Button({title, onPress, variant = "primary", disabled = false}) {
  return <Pressable accessibilityRole="button" disabled={disabled} onPress={onPress} style={({pressed}) => [styles.button, styles[`button${variant[0].toUpperCase()}${variant.slice(1)}`], pressed && !disabled && styles.pressed, disabled && styles.buttonDisabled]}>
    <Text style={[styles.buttonText, styles[`buttonText${variant[0].toUpperCase()}${variant.slice(1)}`]]}>{title}</Text>
  </Pressable>;
}

function MenuItem({active, icon, label, onPress, danger = false}) {
  return <Pressable accessibilityRole="button" onPress={onPress} style={({pressed}) => [styles.menuItem, active && styles.menuItemActive, pressed && styles.pressed]}>
    <Text style={[styles.menuIcon, (active || danger) && styles.menuItemActiveText, danger && styles.menuDangerText]}>{icon}</Text>
    <Text style={[styles.menuLabel, active && styles.menuItemActiveText, danger && styles.menuDangerText]}>{label}</Text>
  </Pressable>;
}

function FilterPill({active, label, onPress}) {
  return <Pressable accessibilityRole="button" onPress={onPress} style={({pressed}) => [styles.filterPill, active && styles.filterPillActive, pressed && styles.pressed]}>
    <Text style={[styles.filterPillText, active && styles.filterPillTextActive]}>{label}</Text>
  </Pressable>;
}

function WorkspaceSwitcher({active, onSelect}) {
  const touchStartX = useRef(null);
  const changeWithGesture = (event) => {
    if (touchStartX.current === null) return;
    const deltaX = event.nativeEvent.pageX - touchStartX.current;
    touchStartX.current = null;
    if (Math.abs(deltaX) < 32) return;
    onSelect(deltaX < 0 ? "veterinary" : "community");
  };

  return <View
    accessibilityRole="tablist"
    accessibilityLabel="Área de la aplicación"
    onTouchStart={(event) => { touchStartX.current = event.nativeEvent.pageX; }}
    onTouchEnd={changeWithGesture}
    style={styles.workspaceSwitcher}
  >
    <Pressable accessibilityRole="tab" accessibilityState={{selected: active === "community"}} onPress={() => onSelect("community")} style={[styles.workspaceOption, active === "community" && styles.workspaceOptionActive]}>
      <Text style={[styles.workspaceOptionText, active === "community" && styles.workspaceOptionTextActive]}>Comunidad</Text>
    </Pressable>
    <Pressable accessibilityRole="tab" accessibilityState={{selected: active === "veterinary"}} onPress={() => onSelect("veterinary")} style={[styles.workspaceOption, active === "veterinary" && styles.workspaceOptionActive]}>
      <Text style={[styles.workspaceOptionText, active === "veterinary" && styles.workspaceOptionTextActive]}>Veterinaria</Text>
    </Pressable>
  </View>;
}

function PermissionRow({icon, label, status}) {
  const labelByStatus = {granted: "Permitido", denied: "No permitido", unknown: "Sin definir"};
  return <View style={styles.permissionRow}><Text style={styles.permissionIcon}>{icon}</Text><Text style={styles.permissionLabel}>{label}</Text><Text style={[styles.permissionStatus, status === "granted" && styles.permissionGranted, status === "denied" && styles.permissionDenied]}>{labelByStatus[status] || labelByStatus.unknown}</Text></View>;
}

function AnimalGlyph({species, style}) {
  const normalized = (species || "").toLowerCase();
  const icon = normalized.includes("gato") || normalized.includes("cat") ? "🐱" : normalized.includes("perro") || normalized.includes("dog") ? "🐶" : "🐾";
  return <Text style={[styles.animalGlyph, style]}>{icon}</Text>;
}

function TravelCredentialCard({animal, credential}) {
  if (!credential) return null;
  return <View style={styles.travelCredentialCard}>
    <View style={styles.credentialTopBar}>
      <View><Text style={styles.credentialOverline}>APP CANINA · VIAJE</Text><Text style={styles.credentialHeading}>Credencial de salud</Text></View>
      <View style={styles.credentialSeal}><Text style={styles.credentialSealText}>✚</Text></View>
    </View>
    <View style={styles.credentialAnimalRow}>
      {animal.photo_url ? <Image source={{uri: animal.photo_url}} style={styles.credentialAnimalPhoto}/> : <View style={styles.credentialAnimalFallback}><AnimalGlyph species={animal.species}/></View>}
      <View style={styles.credentialAnimalInfo}><Text style={styles.credentialAnimalName}>{animal.name}</Text><Text style={styles.credentialAnimalMeta}>{animal.species}{animal.breed ? ` · ${animal.breed}` : ""}</Text><Text style={styles.credentialAnimalMeta}>{animal.microchip ? `ID ${animal.microchip}` : "Identificación no informada"}</Text></View>
    </View>
    <View style={styles.credentialCodePanel}><Text style={styles.credentialLabel}>CÓDIGO TEMPORAL · PRESENTACIÓN VOLUNTARIA</Text><Text selectable style={styles.credentialCode}>{credential.code}</Text><Text style={styles.credentialExpires}>Válida hasta {new Date(credential.expires_at).toLocaleString()}</Text></View>
    <Text style={styles.credentialFootnote}>Esta credencial no comparte tu ubicación ni abre el historial por sí sola.</Text>
  </View>;
}

function AdoptionCard({post, onInterest, onShare}) {
  return <View style={styles.adoptionCard}>
    <View style={styles.adoptionPhotoFrame}>
      {post.photo_url ? <Image source={{uri: post.photo_url}} style={styles.adoptionPhoto}/> : <View style={styles.adoptionPhotoFallback}><AnimalGlyph species={post.species} style={styles.adoptionGlyph}/><Text style={styles.adoptionFallbackText}>Buscando una familia</Text></View>}
      <View style={styles.adoptionBadge}><Text style={styles.adoptionBadgeText}>EN ADOPCIÓN</Text></View>
    </View>
    <View style={styles.adoptionContent}>
      <View style={styles.adoptionTitleRow}><View style={styles.adoptionTitleBlock}><Text style={styles.adoptionName}>{post.name}</Text><Text style={styles.adoptionTraits}>{post.species}{post.breed ? ` · ${post.breed}` : ""}{post.age ? ` · ${post.age}` : ""}</Text></View><Text style={styles.adoptionHeart}>♡</Text></View>
      <Text style={styles.adoptionLocation}>⌖ {post.area}</Text>
      <Text numberOfLines={3} style={styles.adoptionDescription}>{post.description || "Esperando conocer a su próxima familia."}</Text>
      {post.organization?.name ? <View style={styles.adoptionOrganization}><View style={styles.organizationMiniMark}>{post.organization.logo_url ? <Image source={{uri: post.organization.logo_url}} style={styles.organizationMiniLogo}/> : <Text style={styles.organizationMiniLetter}>{post.organization.name[0]}</Text>}</View><Text style={styles.adoptionOrganizationName}>Acompañado por {post.organization.name}</Text></View> : null}

      <Pressable accessibilityRole="button" onPress={onInterest} style={({pressed}) => [styles.adoptionCta, pressed && styles.pressed]}><Text style={styles.adoptionCtaText}>Quiero conocer a {post.name}</Text><Text style={styles.adoptionCtaArrow}>→</Text></Pressable><Button title="Compartir adopción" variant="outline" onPress={onShare}/>
      <ShelterDonation organization={post.organization}/>
    </View>
  </View>;
}

export default function App() {
  const [session, setSession] = useState({generation: 0, notice: "Ingresá para colaborar."});
  return <SafeAreaProvider><CommunityApp key={session.generation} initialNotice={session.notice} allowRestore={session.generation === 0}
    onSessionEnd={notice => setSession(current => ({generation: current.generation + 1, notice}))}/></SafeAreaProvider>;
}

function CommunityApp({initialNotice, onSessionEnd, allowRestore}) {
  const reportLoad = useRef(0);
  const activityLoad = useRef(0);
  const searchRequestsLoad = useRef(0);
  const closingSearch = useRef(false);
  const [confirmFound, setConfirmFound] = useState(false);
  const [finishingSearch, setFinishingSearch] = useState(false);
  const [reportMapState, setReportMapState] = useState({status: 'idle'});
  const authenticating = useRef(false);
  const clientRef = useRef(null);
  if (!clientRef.current) clientRef.current = createSessionClient({
    fetchImpl: fetch, storage: SecureStore, onEnd: onSessionEnd, logoutUrl: `${API}/sesion/cerrar/`,
  });
  const sessionClient = clientRef.current;
  const sessionRequest = sessionClient.request;
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [accountType, setAccountType] = useState("community");
  const [firstName, setFirstName] = useState("");
  const [email, setEmail] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [organizationLocality, setOrganizationLocality] = useState("");
  const [organizationPhone, setOrganizationPhone] = useState("");
  const [organizationAddress, setOrganizationAddress] = useState("");
  const [donationAlias, setDonationAlias] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState(initialNotice);
  const [photoUri, setPhotoUri] = useState("");
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [institutionNotice, setInstitutionNotice] = useState(null);
  const notificationRefresh = useRef(0);
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
  const [selectedReport, setSelectedReport] = useState(null);
  const [sightingArea, setSightingArea] = useState("");
  const [sightingDescription, setSightingDescription] = useState("");
  const [sightingPhoto, setSightingPhoto] = useState(null);
  const [sightingLocation, setSightingLocation] = useState(null);
  const [adoptions, setAdoptions] = useState([]);
  const [adoptionName, setAdoptionName] = useState("");
  const [adoptionSpecies, setAdoptionSpecies] = useState("");
  const [adoptionBreed, setAdoptionBreed] = useState("");
  const [adoptionAge, setAdoptionAge] = useState("");
  const [adoptionArea, setAdoptionArea] = useState("");
  const [adoptionDescription, setAdoptionDescription] = useState("");
  const [adoptionPhoto, setAdoptionPhoto] = useState(null);
  const [selectedAdoption, setSelectedAdoption] = useState(null);
  const [interestMessage, setInterestMessage] = useState("");
  const [adoptionInterests, setAdoptionInterests] = useState([]);
  const [adoptionView, setAdoptionView] = useState("all");
  const [adoptionCounts, setAdoptionCounts] = useState({});
  const [canManageAdoptions, setCanManageAdoptions] = useState(false);
  const [adoptionAudience, setAdoptionAudience] = useState("applicant");
  const [interestsLoading, setInterestsLoading] = useState(false);
  const [interestsError, setInterestsError] = useState("");
  const [pendingVisitId, setPendingVisitId] = useState(null);
  const interestOperation = useRef(false);
  const [myAnimals, setMyAnimals] = useState([]);
  const [selectedAnimal, setSelectedAnimal] = useState(null);
  const [familyInvite, setFamilyInvite] = useState(null);
  const [familyCode, setFamilyCode] = useState("");
  const [newAnimalName, setNewAnimalName] = useState("");
  const [newAnimalSpecies, setNewAnimalSpecies] = useState("dog");
  const [newAnimalBreed, setNewAnimalBreed] = useState("");
  const [newAnimalBirthDate, setNewAnimalBirthDate] = useState("");
  const [newAnimalMicrochip, setNewAnimalMicrochip] = useState("");
  const [newAnimalAllergies, setNewAnimalAllergies] = useState("");
  const [newAnimalPhoto, setNewAnimalPhoto] = useState(null);
  const [travelCredential, setTravelCredential] = useState(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true);
  const [pendingBiometricToken, setPendingBiometricToken] = useState("");
  const [biometricEnabled, setBiometricEnabled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [workspace, setWorkspace] = useState("community");
  const [devicePermissions, setDevicePermissions] = useState({camera: "unknown", location: "unknown", notifications: "unknown"});

  const loadNotifications = async (accessToken = token) => {
    const id = ++notificationRefresh.current;
    const response = await sessionRequest(`${API}/novedades/?count_only=1`, {headers: {Authorization: `Bearer ${accessToken}`}});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail || "No se pudieron consultar las notificaciones.");
    if (notificationRefresh.current === id) setUnreadNotifications(data.unread_count);
  };

  useEffect(() => {
    if (!token) return;
    const refresh = () => { if (AppState.currentState === "active") loadNotifications().catch(() => {}); };
    const subscription = AppState.addEventListener("change", state => { if (state === "active") refresh(); });
    const timer = setInterval(refresh, 60000);
    return () => { clearInterval(timer); subscription.remove(); notificationRefresh.current++; };
  }, [token]);

  useEffect(() => {
    if (!token) return;
    let active = true;
    const openInbox = response => {
      if (!active || !response) return;
      // The inbox revalidates the signed-in account; never trust payload content.
      setScreen("notificaciones");
      loadNotifications().catch(() => {});
      Notifications.clearLastNotificationResponseAsync().catch(() => {});
    };
    const tapped = Notifications.addNotificationResponseReceivedListener(openInbox);
    const received = Notifications.addNotificationReceivedListener(() => loadNotifications().catch(() => {}));
    Notifications.getLastNotificationResponseAsync().then(openInbox).catch(() => {});
    return () => { active = false; tapped.remove(); received.remove(); };
  }, [token]);

  const openNotification = async (item, isCurrent) => {
    const response = await sessionRequest(`${API}/novedades/${item.key}/`, {headers: {Authorization: `Bearer ${token}`}});
    const data = await response.json();
    if (!isCurrent()) return;
    if (!response.ok) throw Error(data.detail || "La novedad ya no está disponible.");
    if (data.target === "report") {
      const detail = await sessionRequest(`${API}/avisos/${data.report_id}/`, {headers: {Authorization: `Bearer ${token}`}});
      const reportData = await detail.json();
      if (!isCurrent()) return;
      if (!detail.ok) throw Error(reportData.detail || "No pudimos abrir el aviso.");
      reportLoad.current++; setConfirmFound(false); setSelectedReport(reportData.report); setReportMapState({status: "ready"}); setScreen("detalle");
    } else if (data.target === "search_request") {
      searchRequestsLoad.current++; setMyRequests([data.request]); setScreen("mis-solicitudes");
    } else if (data.target === "adoption") {
      activityLoad.current++; setInterestsLoading(false); setInterestsError("");
      setAdoptionView(data.interest.is_archived ? "archived" : "all"); setAdoptionCounts({});
      setAdoptionInterests([data.interest]); setAdoptionAudience("applicant"); setScreen("mi-actividad");
    } else if (data.target === "institution") {
      activityLoad.current++; setInterestsLoading(false); setInterestsError("");
      setCanManageAdoptions(true); setAdoptionAudience("institution");
      setInstitutionNotice({interests: [data.interest], counts: {}, status_choices: data.status_choices, has_next: false});
      setScreen("mi-actividad");
    } else { throw Error("No pudimos identificar el contenido de esta novedad."); }
    setMessage("");
    try {
      const read = await sessionRequest(`${API}/novedades/${item.key}/leer/`, {
        method: "POST", headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"},
        body: JSON.stringify({activity_at: data.activity_at}),
      });
      if (!read.ok) throw Error("No pudimos guardar la lectura.");
      await loadNotifications();
    } catch { setMessage("Abrimos la novedad, pero no pudimos actualizar su lectura. Podés volver a abrirla desde Notificaciones."); }
  };

  const getDeviceKey = async () => {
    let deviceKey = await SecureStore.getItemAsync("community-device-key");
    if (!deviceKey) {
      deviceKey = `device-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
      await sessionClient.store("community-device-key", deviceKey);
    }
    return deviceKey;
  };

  const permissionStatus = (permission) => permission?.granted ? "granted" : permission?.status === "denied" ? "denied" : "unknown";

  const syncDevicePermissions = async (accessToken = token) => {
    if (!accessToken) return;
    try {
      const [camera, location, notifications, deviceKey] = await Promise.all([
        ImagePicker.getCameraPermissionsAsync(),
        Location.getForegroundPermissionsAsync(),
        Notifications.getPermissionsAsync(),
        getDeviceKey(),
      ]);
      const response = await sessionRequest(`${API}/dispositivos/permisos/`, {
        method: "POST",
        headers: {"Content-Type": "application/json", Authorization: `Bearer ${accessToken}`},
        body: JSON.stringify({device_key: deviceKey, device_name: Device.modelName || "Dispositivo móvil", platform: Platform.OS, camera: permissionStatus(camera), location: permissionStatus(location), notifications: permissionStatus(notifications)}),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudieron actualizar los permisos.");
      setDevicePermissions(data.device);
    } catch (error) {
      setMessage(error.message || "No se pudo consultar el estado de permisos.");
    }
  };

  const activateSession = async (accessToken, successMessage) => {
    sessionClient.assertActive();
    const response = await sessionRequest(`${API}/avisos/`, {headers: {Authorization: `Bearer ${accessToken}`}});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail || "No se pudo validar la sesión.");
    await sessionClient.store("community-token", accessToken);
    sessionClient.assertActive();
    setPassword(""); setPasswordConfirmation("");
    setReports(data.reports);
    setToken(accessToken); setScreen("panel");
    try {
      await loadNotifications(accessToken);
      await syncDevicePermissions(accessToken);
      if (successMessage) setMessage(successMessage);
    } catch (error) {
      setMessage(error.message || "No se pudo restaurar la sesión.");
    }
  };

  const restoreSession = async () => {
    try {
      const savedToken = await SecureStore.getItemAsync("community-token");
      const wantsBiometric = await SecureStore.getItemAsync("community-biometric-enabled");
      sessionClient.assertActive();
      setBiometricEnabled(wantsBiometric === "true");
      if (!savedToken) return;
      const hasHardware = await LocalAuthentication.hasHardwareAsync();
      const isEnrolled = hasHardware && await LocalAuthentication.isEnrolledAsync();
      if (wantsBiometric === "true" && isEnrolled) {
        setPendingBiometricToken(savedToken);
        setMessage("Confirmá tu identidad para abrir la comunidad.");
      } else {
        await activateSession(savedToken, "Sesión restaurada.");
      }
    } catch (error) {
      setMessage("No se pudo restaurar la sesión anterior.");
    } finally { setIsRestoringSession(false); }
  };

  useEffect(() => {
    if (allowRestore) restoreSession(); else setIsRestoringSession(false);
    return () => sessionClient.dispose();
  }, []);

  const unlockWithBiometrics = async () => {
    try {
      const result = await LocalAuthentication.authenticateAsync({promptMessage: "Ingresar a Lazuna", cancelLabel: "Cancelar", fallbackLabel: "Usar contraseña"});
      if (!result.success) { setMessage("No se pudo validar la huella. Podés usar tu usuario y contraseña."); return; }
      const savedToken = pendingBiometricToken || await SecureStore.getItemAsync("community-token");
      if (!savedToken) { setPendingBiometricToken(""); return; }
      setPendingBiometricToken("");
      await activateSession(savedToken, "Sesión desbloqueada con biometría.");
    } catch (error) { setMessage("La biometría no está disponible en este teléfono."); }
  };

  const enableBiometrics = async () => {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    const isEnrolled = hasHardware && await LocalAuthentication.isEnrolledAsync();
    if (!isEnrolled) { setMessage("No hay huella, rostro o bloqueo biométrico configurado en este teléfono."); return; }
    const result = await LocalAuthentication.authenticateAsync({promptMessage: "Confirmá para activar el acceso biométrico", cancelLabel: "Cancelar"});
    if (!result.success) { setMessage("No se activó el acceso biométrico."); return; }
    await sessionClient.store("community-biometric-enabled", "true"); setBiometricEnabled(true); setMessage("Acceso con huella activado para este teléfono.");
  };

  const logout = async () => {
    setPassword(""); setPasswordConfirmation(""); setMessage("Cerrando sesión…");
    await sessionClient.end("Sesión cerrada en este teléfono.", token || pendingBiometricToken);
  };

  const loadReports = async (accessToken = token, state = reportState, query = reportQuery) => {
    try {
      const params = new URLSearchParams({estado: state});
      if (query.trim()) params.set("q", query.trim());
      const response = await sessionRequest(`${API}/avisos/?${params.toString()}`, {headers: {Authorization: `Bearer ${accessToken}`}});
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
    try {
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
      const pushToken = (await Notifications.getExpoPushTokenAsync({projectId})).data;
      const response = await sessionRequest(`${API}/dispositivos/push/`, {
        method: "POST",
        headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`},
        body: JSON.stringify({push_token: pushToken, platform: Platform.OS}),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo registrar este dispositivo.");
      await syncDevicePermissions();
      setMessage("Alertas activadas en este teléfono.");
    } catch (error) {
      setMessage(error.message);
    }
  };

  const login = async () => {
    if (authenticating.current) return;
    authenticating.current = true;
    try {
      const response = await sessionRequest(`${API}/sesion/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password, device_name: "App móvil"}),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo iniciar sesión.");
      await activateSession(data.token, `Sesión iniciada: ${data.user.username}`);
    } catch (error) {
      setMessage(error.message);
    } finally { authenticating.current = false; setPassword(""); setPasswordConfirmation(""); }
  };

  const register = async () => {
    if (authenticating.current) return;
    authenticating.current = true;
    try {
      const response = await sessionRequest(`${API}/registro/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          username,
          account_type: accountType,
          first_name: firstName,
          email,
          organization_name: organizationName,
          locality: organizationLocality,
          organization_phone: organizationPhone,
          organization_address: organizationAddress,
          donation_alias: donationAlias,
          password,
          password_confirmation: passwordConfirmation,
          device_name: "App móvil",
        }),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo crear la cuenta.");
      await activateSession(data.token, data.detail || `Cuenta creada. ¡Gracias por colaborar, ${data.user.username}!`);
    } catch (error) {
      setMessage(error.message);
    } finally { authenticating.current = false; setPassword(""); setPasswordConfirmation(""); }
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

  const selectImage = async (fromCamera, onSelected, purpose) => {
    try {
      const permission = fromCamera
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        setMessage(fromCamera ? "La cámara no está autorizada. Permitila desde Ajustes o elegí una foto de la galería." : "El acceso a fotos no está autorizado. Podés usar la cámara o habilitar Fotos desde Ajustes.");
        return;
      }
      const options = {mediaTypes: ["images"], allowsEditing: true, quality: 0.8};
      const result = fromCamera ? await ImagePicker.launchCameraAsync(options) : await ImagePicker.launchImageLibraryAsync(options);
      if (result.canceled) {
        setMessage("No seleccionaste una foto.");
        return;
      }
      const asset = result.assets?.[0];
      if (!asset?.uri) throw Error("El teléfono no devolvió una imagen utilizable.");
      onSelected(asset);
      setMessage(`Foto lista para ${purpose}. Se adjuntará al guardar.`);
    } catch (error) {
      setMessage(`No se pudo abrir ${fromCamera ? "la cámara" : "la galería"}: ${error.message || "revisá los permisos del teléfono."}`);
    }
  };

  const takePhoto = () => selectImage(true, asset => setPhotoUri(asset.uri), "la próxima publicación");

  const chooseRequestPhoto = (fromCamera = false) => selectImage(fromCamera, setRequestPhoto, "la solicitud");

  const chooseSightingPhoto = (fromCamera = false) => selectImage(fromCamera, setSightingPhoto, "el avistamiento");

  const useSightingLocation = async () => {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") {
      setMessage("No compartiste ubicación. Indicá la zona manualmente.");
      return;
    }
    const location = await Location.getCurrentPositionAsync({accuracy: Location.Accuracy.Balanced});
    setSightingLocation({latitude: location.coords.latitude, longitude: location.coords.longitude});
    setMessage("Ubicación añadida. El aviso público mostrará solo una zona aproximada.");
  };

  const openReport = async (report) => {
    setConfirmFound(false);
    const loadId = ++reportLoad.current;
    setSelectedReport({...report, search_map: undefined}); setScreen("detalle");
    setReportMapState({status: 'loading'});
    try {
      const response = await sessionRequest(`${API}/avisos/${report.id}/`, {headers: {Authorization: `Bearer ${token}`}});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || 'No se pudo actualizar la ubicación.');
      if (loadId !== reportLoad.current) return;
      setSelectedReport(data.report); setReportMapState({status: 'ready'});
    } catch (error) {
      if (loadId === reportLoad.current) setReportMapState({status: 'error', error: error.message});
    }
  };

  const finishSearch = async () => {
    if (!selectedReport || closingSearch.current) return;
    closingSearch.current = true; setFinishingSearch(true);
    const reportId = selectedReport.id;
    const loadId = ++reportLoad.current;
    try {
      const response = await sessionRequest(`${API}/avisos/${reportId}/encontrado/`, {
        method: "POST", headers: {Authorization: `Bearer ${token}`},
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo finalizar. Actualizá el aviso y reintentá.");
      setReports(current => current.filter(item => item.id !== reportId));
      if (loadId === reportLoad.current) {
        setSelectedReport(current => current?.id === reportId ? {...current, status: data.status, can_finish_search: false} : current);
        setConfirmFound(false); setMessage(data.detail);
      }
    } catch (error) { if (loadId === reportLoad.current) setMessage(error.message); }
    finally { closingSearch.current = false; setFinishingSearch(false); }
  };

  const resetSighting = () => {
    setSightingArea(""); setSightingDescription(""); setSightingPhoto(null); setSightingLocation(null);
  };

  const submitSighting = async () => {
    if (!selectedReport) return;
    try {
      const form = new FormData();
      form.append("area", sightingArea); form.append("description", sightingDescription);
      if (sightingLocation) {
        form.append("latitude", String(sightingLocation.latitude)); form.append("longitude", String(sightingLocation.longitude));
      }
      if (sightingPhoto?.uri) form.append("photo", {uri: sightingPhoto.uri, name: sightingPhoto.fileName || "avistamiento.jpg", type: sightingPhoto.mimeType || "image/jpeg"});
      const response = await sessionRequest(`${API}/avisos/${selectedReport.id}/avistamientos/`, {method: "POST", headers: {Authorization: `Bearer ${token}`}, body: form});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo compartir el avistamiento.");
      resetSighting(); setScreen("panel"); setMessage(data.detail); await loadReports();
    } catch (error) {
      setMessage(error.message);
    }
  };

  const loadMySearchRequests = async (accessToken = token) => {
    const loadId = ++searchRequestsLoad.current;
    try {
      const response = await sessionRequest(`${API}/solicitudes-busqueda/mias/`, {headers: {Authorization: `Bearer ${accessToken}`}});
      const data = await response.json();
      if (loadId !== searchRequestsLoad.current) return;
      if (!response.ok) throw Error(data.detail || "No se pudieron cargar tus solicitudes.");
      setMyRequests(data.requests);
    } catch (error) {
      if (loadId === searchRequestsLoad.current) setMessage(error.message);
    }
  };

  const loadAdoptions = async () => {
    try {
      const response = await sessionRequest(`${API}/adopciones/`, {headers: {Authorization: `Bearer ${token}`}});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudieron cargar las adopciones.");
      setAdoptions(data.adoptions);
    } catch (error) { setMessage(error.message); }
  };

  const submitAdoption = async () => {
    try {
      const form = new FormData();
      form.append("name", adoptionName); form.append("species", adoptionSpecies); form.append("breed", adoptionBreed);
      form.append("age", adoptionAge); form.append("area", adoptionArea); form.append("description", adoptionDescription);
      if (adoptionPhoto?.uri) form.append("photo", {uri: adoptionPhoto.uri, name: adoptionPhoto.fileName || "adopcion.jpg", type: adoptionPhoto.mimeType || "image/jpeg"});
      const response = await sessionRequest(`${API}/adopciones/solicitar/`, {method: "POST", headers: {Authorization: `Bearer ${token}`}, body: form});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo enviar la publicación.");
      setAdoptionName(""); setAdoptionSpecies(""); setAdoptionBreed(""); setAdoptionAge(""); setAdoptionArea(""); setAdoptionDescription(""); setAdoptionPhoto(null);
      setScreen("adopciones"); setMessage(data.detail);
    } catch (error) { setMessage(error.message); }
  };

  const loadAdoptionInterests = async (nextView = adoptionView) => {
    if (typeof nextView !== "string") nextView = adoptionView;
    setInstitutionNotice(null);
    if (interestOperation.current) return;
    interestOperation.current = true;
    const loadId = ++activityLoad.current;
    setInterestsLoading(true); setInterestsError("");
    try {
      const response = await sessionRequest(`${API}/adopciones/mis-intereses/${nextView === "archived" ? "?view=archived" : ""}`, {headers: {Authorization: `Bearer ${token}`}});
      const data = await response.json();
      if (loadId !== activityLoad.current) return;
      if (!response.ok) throw Error(data.detail || "No se pudo cargar tu actividad.");
      setAdoptionInterests(data.interests);
      setAdoptionView(nextView); setAdoptionCounts(data.counts || {});
      setCanManageAdoptions(data.can_manage_adoption_requests === true);
    } catch (error) { if (loadId === activityLoad.current) setInterestsError(error.message || "No pudimos actualizar. Revisá tu conexión y volvé a intentar."); }
    finally { interestOperation.current = false; if (loadId === activityLoad.current) setInterestsLoading(false); }
  };

  const archiveAdoptionInterest = async (item, animate) => {
    if (interestOperation.current) return;
    interestOperation.current = true;
    const loadId = ++activityLoad.current;
    setPendingVisitId(item.id); setInterestsError("");
    try {
      const response = await sessionRequest(`${API}/adopciones/archivo/applicant/${item.id}/`, {
        method: "POST", headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"},
        body: JSON.stringify({action: item.is_archived ? "restore" : "archive", expected_updated_at: item.updated_at}),
      });
      const data = await response.json();
      if (loadId !== activityLoad.current) return;
      if (!response.ok) throw Error(data.detail || "No se pudo archivar. Actualizá para comprobar el resultado.");
      if (!item.is_archived) await animate?.();
      if (loadId !== activityLoad.current) return;
      setMessage(data.detail);
      setAdoptionInterests(current => current.filter(existing => existing.id !== item.id));
      interestOperation.current = false;
      await loadAdoptionInterests(adoptionView);
    } catch (error) {
      if (loadId === activityLoad.current) setInterestsError(error.message || "Revisá tu conexión y actualizá la bandeja.");
    } finally { interestOperation.current = false; setPendingVisitId(null); }
  };

  const requestAdoptionVisit = async interestId => {
    if (interestOperation.current) return;
    interestOperation.current = true;
    setPendingVisitId(interestId); setInterestsError("");
    try {
      const response = await sessionRequest(`${API}/adopciones/solicitudes/${interestId}/visita/`, {
        method: "POST", headers: {Authorization: `Bearer ${token}`},
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo solicitar la visita. Actualizá las solicitudes antes de reintentar.");
      setAdoptionInterests(current => current.map(item => item.id === interestId ? data.interest : item));
      setMessage(data.detail);
    } catch (error) { setInterestsError(error.message || "Revisá tu conexión y actualizá para comprobar si la visita quedó solicitada."); }
    finally { interestOperation.current = false; setPendingVisitId(null); }
  };

  const loadMyAnimals = async (accessToken = token) => {
    try {
      const response = await sessionRequest(`${API}/mis-animales/`, {headers: {Authorization: `Bearer ${accessToken}`}});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudieron cargar tus animales.");
      setMyAnimals(data.animals);
    } catch (error) { setMessage(error.message); }
  };

  const resetNewAnimal = () => {
    setNewAnimalName(""); setNewAnimalSpecies("dog"); setNewAnimalBreed(""); setNewAnimalBirthDate("");
    setNewAnimalMicrochip(""); setNewAnimalAllergies(""); setNewAnimalPhoto(null);
  };

  const submitNewAnimal = async () => {
    try {
      const form = new FormData();
      form.append("name", newAnimalName); form.append("species", newAnimalSpecies);
      form.append("breed", newAnimalBreed); form.append("birth_date", newAnimalBirthDate);
      form.append("microchip", newAnimalMicrochip); form.append("allergies", newAnimalAllergies);
      if (newAnimalPhoto?.uri) form.append("photo", {uri: newAnimalPhoto.uri, name: newAnimalPhoto.fileName || "mi-animal.jpg", type: newAnimalPhoto.mimeType || "image/jpeg"});
      const response = await sessionRequest(`${API}/mis-animales/`, {method: "POST", headers: {Authorization: `Bearer ${token}`}, body: form});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo agregar tu animal.");
      resetNewAnimal(); setMyAnimals(current => [...current, data.animal].sort((a, b) => a.name.localeCompare(b.name)));
      setScreen("mis-animales"); setMessage(data.detail);
    } catch (error) { setMessage(error.message); }
  };

  const openAnimal = (animal) => {
    setSelectedAnimal(animal); setFamilyInvite(null); setTravelCredential(null); setScreen("mi-animal");
  };

  const updateSharingConsent = async (sharingEnabled) => {
    if (!selectedAnimal) return;
    try {
      const response = await sessionRequest(`${API}/mis-animales/${selectedAnimal.id}/`, {
        method: "POST",
        headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`},
        body: JSON.stringify({sharing_enabled: sharingEnabled}),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo actualizar la preferencia.");
      setSelectedAnimal(data.animal);
      setMyAnimals(current => current.map(animal => animal.id === data.animal.id ? data.animal : animal));
      setMessage(sharingEnabled ? "Autorizaste el historial compartido para atención temporal." : "Desactivaste el historial compartido.");
    } catch (error) { setMessage(error.message); }
  };

  const createTravelCredential = async () => {
    if (!selectedAnimal) return;
    try {
      const response = await sessionRequest(`${API}/mis-animales/${selectedAnimal.id}/credencial/`, {
        method: "POST", headers: {Authorization: `Bearer ${token}`},
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo crear la credencial.");
      setTravelCredential(data); setMessage(data.detail);
    } catch (error) { setMessage(error.message); }
  };

  const createFamilyInvite = async () => {
    if (!selectedAnimal) return;
    try {
      const response = await sessionRequest(`${API}/mis-animales/${selectedAnimal.id}/invitaciones-familiares/`, {
        method: "POST", headers: {Authorization: `Bearer ${token}`},
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo crear el código familiar.");
      setFamilyInvite({...data, animalId: selectedAnimal.id, animalName: selectedAnimal.name}); setMessage(data.detail);
    } catch (error) { setMessage(error.message); }
  };

  const shareFamilyInvite = async (copyOnly = false) => {
    if (!familyInvite || familyInvite.animalId !== selectedAnimal?.id) return;
    if (!(new Date(familyInvite.expires_at).getTime() > Date.now())) {
      setMessage("Este código venció. Creá uno nuevo para compartir la ficha.");
      return;
    }
    try {
      if (copyOnly) {
        await Clipboard.setStringAsync(familyInvite.code);
        setMessage("Código copiado. Ya podés pegarlo en WhatsApp.");
      } else {
        const link = familyInvite.share_url || `${API.replace(/\/extraviados\/api\/v1\/?$/, '')}/mis-animales/agregar-con-codigo/#code=${encodeURIComponent(familyInvite.code)}`;
        await Share.share({message: familyInvite.share_text || `Te comparto la ficha de ${familyInvite.animalName} en Lazuna.\n\nAbrí el enlace, ingresá o creá tu cuenta y confirmá la invitación:\n${link}\n\nCódigo manual: ${familyInvite.code}\n\nVence el ${new Date(familyInvite.expires_at).toLocaleString()} y se usa una sola vez. Es un acceso privado: no lo reenvíes.`});
      }
    } catch (error) {
      setMessage(copyOnly ? "No se pudo copiar el código. Podés mantenerlo presionado para copiarlo manualmente." : "No se pudo abrir el menú para compartir. Probá copiar el código.");
    }
  };

  const shareAdoption = async (post) => {
    try {
      await Share.share({message: [
        `${post.name} busca un hogar 🐾`,
        [post.species, post.breed, post.age].filter(Boolean).join(" · "),
        post.area ? `Zona: ${post.area}` : "",
        post.description,
        post.organization?.name ? `Refugio: ${post.organization.name}` : "",
        `Para expresar interés, abrí Lazuna → Comunidad → Adopciones y buscá a ${post.name}.`,
      ].filter(Boolean).join("\n\n")});
    } catch (error) {
      setMessage("No se pudo abrir el menú para compartir. Intentá nuevamente.");
    }
  };

  const acceptFamilyInvite = async () => {
    try {
      const response = await sessionRequest(`${API}/familia/aceptar-invitacion/`, {
        method: "POST",
        headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`},
        body: JSON.stringify({code: familyCode.trim()}),
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo vincular el animal.");
      setFamilyCode(""); setMyAnimals(current => [...current.filter(animal => animal.id !== data.animal.id), data.animal].sort((a, b) => a.name.localeCompare(b.name)));
      openAnimal(data.animal); setMessage(data.detail);
    } catch (error) { setMessage(error.message); }
  };

  const revokeFamilyAccess = async (accessId, memberName) => {
    if (!selectedAnimal) return;
    try {
      const response = await sessionRequest(`${API}/mis-animales/${selectedAnimal.id}/familia/${accessId}/revocar/`, {
        method: "POST", headers: {Authorization: `Bearer ${token}`},
      });
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo revocar el acceso.");
      const updated = {...selectedAnimal, family_members: selectedAnimal.family_members.filter(member => member.access_id !== accessId)};
      setSelectedAnimal(updated); setMyAnimals(current => current.map(animal => animal.id === updated.id ? updated : animal));
      setMessage(`${memberName}: ${data.detail}`);
    } catch (error) { setMessage(error.message); }
  };

  const submitAdoptionInterest = async () => {
    if (!selectedAdoption) return;
    try {
      const response = await sessionRequest(`${API}/adopciones/${selectedAdoption.id}/intereses/`, {method: "POST", headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`}, body: JSON.stringify({message: interestMessage})});
      const data = await response.json();
      if (!response.ok) throw Error(data.detail || "No se pudo enviar tu interés.");
      setInterestMessage(""); setAdoptionAudience("applicant"); setScreen("mi-actividad"); setMessage(data.detail); await loadAdoptionInterests();
    } catch (error) { setMessage(error.message); }
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
      const response = await sessionRequest(`${API}/solicitudes-busqueda/${editingRequest ? `${editingRequest.id}/editar/` : ""}`, {
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

  const navigate = (nextScreen, load) => {
    setScreen(nextScreen);
    setMenuOpen(false);
    load?.();
  };

  const switchWorkspace = (nextWorkspace) => {
    if (nextWorkspace === workspace) return;
    setWorkspace(nextWorkspace);
    setMenuOpen(false);
    if (nextWorkspace === "veterinary") {
      setScreen("veterinaria");
      loadMyAnimals();
    } else {
      setScreen("panel");
      loadReports();
    }
  };

  const clinicalRecordCount = myAnimals.reduce((total, animal) => total + (animal.clinical_records?.length || 0), 0);
  const sharedHistoryCount = myAnimals.filter(animal => animal.sharing_enabled).length;

  return <SafeAreaView style={styles.screen}>
    <ScrollView contentContainerStyle={styles.content}>
      {!token ? <><Text style={styles.title}>Lazuna</Text><Text style={styles.subtitle}>Comunidad · animales extraviados</Text></> : null}
      {!token ? isRestoringSession ? <View style={styles.stack}><Text style={styles.help}>Preparando tu sesión segura…</Text></View> : pendingBiometricToken ? <View style={styles.stack}><Text style={styles.sectionTitle}>Volvé a ingresar</Text><Text style={styles.help}>Tu sesión está guardada en este teléfono y protegida con biometría.</Text><Button title="Ingresar con huella" onPress={unlockWithBiometrics}/><Button title="Usar otra cuenta" onPress={logout}/></View> : <View style={styles.stack}>
      {isRegistering ? <><Text style={styles.help}>Elegí cómo vas a participar: como colaborador/a para ayudar o adoptar, o en representación de una veterinaria o refugio. Las instituciones necesitan aprobación para administrar publicaciones o datos clínicos.</Text><View style={styles.field}><Text style={styles.fieldLabel}>Quiero registrarme como</Text><View style={styles.filterRow}><FilterPill active={accountType === "community"} label="Colaborador/a" onPress={() => setAccountType("community")}/><FilterPill active={accountType === "veterinary"} label="Veterinaria" onPress={() => setAccountType("veterinary")}/><FilterPill active={accountType === "shelter"} label="Refugio" onPress={() => setAccountType("shelter")}/></View></View></> : null}
      {isRegistering ? <View style={styles.field}><Text style={styles.fieldLabel}>Nombre <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="Ej.: Sofía" placeholderTextColor="#6c8378" value={firstName} onChangeText={setFirstName} style={styles.input}/></View> : null}
      <View style={styles.field}><Text style={styles.fieldLabel}>Usuario</Text><TextInput placeholder="Elegí un usuario" placeholderTextColor="#6c8378" value={username} onChangeText={setUsername} autoCapitalize="none" style={styles.input}/></View>
      {isRegistering ? <View style={styles.field}><Text style={styles.fieldLabel}>Correo electrónico <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="nombre@correo.com" placeholderTextColor="#6c8378" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" style={styles.input}/></View> : null}
      {isRegistering && accountType !== "community" ? <><View style={styles.field}><Text style={styles.fieldLabel}>Nombre de {accountType === "veterinary" ? "la veterinaria" : "el refugio"}</Text><TextInput placeholder={accountType === "veterinary" ? "Ej.: Veterinaria del Parque" : "Ej.: Patitas del Sur"} placeholderTextColor="#6c8378" value={organizationName} onChangeText={setOrganizationName} style={styles.input}/></View><View style={styles.field}><Text style={styles.fieldLabel}>Localidad</Text><TextInput placeholder="Ej.: Avellaneda" placeholderTextColor="#6c8378" value={organizationLocality} onChangeText={setOrganizationLocality} style={styles.input}/></View><View style={styles.field}><Text style={styles.fieldLabel}>Teléfono <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="Ej.: 11 5555 1234" placeholderTextColor="#6c8378" value={organizationPhone} onChangeText={setOrganizationPhone} keyboardType="phone-pad" style={styles.input}/></View><View style={styles.field}><Text style={styles.fieldLabel}>Dirección <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="Ej.: Calle 123" placeholderTextColor="#6c8378" value={organizationAddress} onChangeText={setOrganizationAddress} style={styles.input}/></View><View style={styles.field}><Text style={styles.fieldLabel}>{accountType === "veterinary" ? "Alias para cobrar a clientes" : "Alias para colaborar"} <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder={accountType === "veterinary" ? "Ej.: veterinaria.parque" : "Ej.: refugio.patitas"} placeholderTextColor="#6c8378" value={donationAlias} onChangeText={setDonationAlias} autoCapitalize="none" style={styles.input}/></View></> : null}
      <View style={styles.field}><Text style={styles.fieldLabel}>Contraseña</Text><TextInput placeholder="Mínimo 8 caracteres" placeholderTextColor="#6c8378" value={password} onChangeText={setPassword} secureTextEntry style={styles.input}/></View>
      {isRegistering ? <View style={styles.field}><Text style={styles.fieldLabel}>Repetir contraseña</Text><TextInput placeholder="Repetí tu contraseña" placeholderTextColor="#6c8378" value={passwordConfirmation} onChangeText={setPasswordConfirmation} secureTextEntry style={styles.input}/></View> : null}
      <Button title={isRegistering ? "Crear cuenta" : "Ingresar"} onPress={isRegistering ? register : login}/>
      <Button title={isRegistering ? "Ya tengo una cuenta" : "Crear una cuenta para colaborar"} onPress={() => { setIsRegistering(!isRegistering); setMessage(isRegistering ? "Ingresá para colaborar." : "Completá tus datos para crear una cuenta."); }}/>
    </View> : <View style={styles.stack}>
      <View style={styles.appHeader}>
        <View style={styles.appHeaderTop}>
          <View style={styles.brandGroup}><View style={styles.brandMark}><Text style={styles.brandMarkText}>✚</Text></View><View><Text style={styles.appBrand}>Lazuna</Text><Text style={styles.appContext}>{workspace === "community" ? "Comunidad" : "Veterinaria"}</Text></View></View>
          <Pressable accessibilityRole="button" accessibilityLabel={`Notificaciones, ${unreadNotifications} sin leer`} onPress={() => navigate("notificaciones")} style={styles.notificationsAccess}>
            <Text style={styles.notificationsAccessText}>Novedades</Text>
            {unreadNotifications > 0 ? <View style={styles.notificationsBadge}><Text style={styles.notificationsBadgeText}>{unreadNotifications > 99 ? "99+" : unreadNotifications}</Text></View> : null}
          </Pressable>
          <Pressable accessibilityRole="button" accessibilityLabel="Abrir menú" onPress={() => setMenuOpen(true)} style={({pressed}) => [styles.menuTrigger, pressed && styles.pressed]}><Text style={styles.menuTriggerText}>☰</Text></Pressable>
        </View>
        <WorkspaceSwitcher active={workspace} onSelect={switchWorkspace}/>
      </View>
      <Modal visible={menuOpen} transparent animationType="slide" onRequestClose={() => setMenuOpen(false)}>
        <SafeAreaProvider><View style={styles.modalScrim}><Pressable style={styles.scrimTouch} onPress={() => setMenuOpen(false)}/><SafeAreaView edges={["bottom", "left", "right"]} style={styles.menuSheet}>
          <View style={styles.sheetHandle}/><View style={styles.sheetHeading}><View><Text style={styles.menuHeading}>{workspace === "community" ? "Comunidad" : "Veterinaria"}</Text><Text style={styles.menuSubheading}>{workspace === "community" ? "Ayudá a encontrar y adoptar." : "Tus animales y su atención."}</Text></View><Pressable accessibilityRole="button" onPress={() => setMenuOpen(false)} style={styles.closeButton}><Text style={styles.closeButtonText}>×</Text></Pressable></View>
          <WorkspaceSwitcher active={workspace} onSelect={switchWorkspace}/>
          {workspace === "community" ? <>
            <MenuItem active={screen === "panel"} icon="⌂" label="Panel" onPress={() => navigate("panel", loadReports)}/>
            <MenuItem active={screen === "buscar"} icon="⌕" label="Buscar animales" onPress={() => navigate("buscar")}/>
            <MenuItem icon="＋" label="Pedir una búsqueda" onPress={() => { resetSearchRequest(); navigate("solicitud"); }}/>
            <MenuItem active={screen === "mis-solicitudes"} icon="▤" label="Mis solicitudes" onPress={() => navigate("mis-solicitudes", loadMySearchRequests)}/>
            <MenuItem active={screen === "adopciones"} icon="♡" label="Adopciones" onPress={() => navigate("adopciones", loadAdoptions)}/>
            <MenuItem active={screen === "mi-actividad"} icon="◷" label="Mi actividad" onPress={() => navigate("mi-actividad", loadAdoptionInterests)}/>
          </> : <>
            <MenuItem active={screen === "veterinaria"} icon="⌂" label="Panel veterinaria" onPress={() => navigate("veterinaria", loadMyAnimals)}/>
            <MenuItem active={screen === "mis-animales" || screen === "mi-animal" || screen === "nuevo-animal"} icon="🐾" label="Mis animales e historial" onPress={() => navigate("mis-animales", loadMyAnimals)}/>
            <MenuItem active={screen === "vincular-familia"} icon="⌘" label="Vincular mascota familiar" onPress={() => { setFamilyCode(""); navigate("vincular-familia"); }}/>
          </>}
          <View style={styles.menuDivider}/><MenuItem active={screen === "notificaciones"} icon="◉" label={`Notificaciones${unreadNotifications ? ` (${unreadNotifications})` : ""}`} onPress={() => navigate("notificaciones")}/><MenuItem active={screen === "ajustes"} icon="⚙" label="Mi teléfono y alertas" onPress={() => navigate("ajustes")}/><MenuItem danger icon="↪" label="Cerrar sesión" onPress={logout}/>
        </SafeAreaView></View></SafeAreaProvider>
      </Modal>
      {screen === "panel" ? <View style={styles.stack}>
        <View style={styles.panelIntro}><Text style={styles.sectionKicker}>COMUNIDAD ACTIVA</Text><Text style={styles.sectionTitle}>Animales que necesitan ayuda</Text><Text style={styles.help}>Revisá avisos reales y colaborá solo si contás con información segura.</Text></View>
        <View style={styles.filterRow}><FilterPill active={reportState === "activos"} label="Se buscan" onPress={() => changeReportState("activos")}/><FilterPill active={reportState === "encontrados"} label="Encontrados" onPress={() => changeReportState("encontrados")}/><FilterPill label="Actualizar" onPress={() => loadReports()}/></View>
        {reports.length ? reports.map(report => <View key={report.id} style={styles.reportCard}>
          {report.photo_url ? <Image source={{uri: report.photo_url}} style={styles.reportPhoto}/> : <View style={styles.reportPhotoPlaceholder}><Text style={styles.reportPhotoIcon}>{report.species?.toLowerCase().includes("gato") ? "🐱" : report.species?.toLowerCase().includes("perro") ? "🐶" : "🐾"}</Text><Text style={styles.reportPhotoCaption}>Sin foto disponible</Text></View>}
          <View style={styles.reportContent}><Text style={styles.notificationTitle}>{report.name} · {report.species}</Text><Text style={styles.notificationArea}>⌖ {report.area}</Text><Text style={styles.reportMeta}>{report.status === "resolved" ? "Encontrado" : "Se busca"}</Text><Text>{report.description || "Sin señas particulares cargadas."}</Text><Button title="Ver aviso" onPress={() => openReport(report)}/></View>
        </View>) : <Text style={styles.empty}>No hay avisos en esta sección por ahora.</Text>}
      </View> : null}
      {screen === "buscar" ? <View style={styles.stack}>
        <Text style={styles.sectionTitle}>Buscar un animal</Text>
        <View style={styles.field}><Text style={styles.fieldLabel}>Nombre</Text><TextInput placeholder="Ej.: Luna" placeholderTextColor="#6c8378" value={reportQuery} onChangeText={setReportQuery} style={styles.input}/></View>
        <Button title="Buscar entre los avisos" onPress={() => loadReports(token, reportState, reportQuery)}/>
        {reports.map(report => <View key={report.id} style={styles.reportCard}>{report.photo_url ? <Image source={{uri: report.photo_url}} style={styles.reportPhoto}/> : <View style={styles.reportPhotoPlaceholder}><Text style={styles.reportPhotoIcon}>🐾</Text></View>}<View style={styles.reportContent}><Text style={styles.notificationTitle}>{report.name} · {report.species}</Text><Text style={styles.notificationArea}>⌖ {report.area}</Text><Button title="Ver aviso" onPress={() => openReport(report)}/></View></View>)}
      </View> : null}
      {screen === "detalle" && selectedReport ? <View style={styles.stack}>
        <Button title="← Volver al panel" onPress={() => setScreen("panel")}/>
        {selectedReport.photo_url ? <Image source={{uri: selectedReport.photo_url}} style={styles.detailPhoto}/> : <View style={styles.reportPhotoPlaceholder}><Text style={styles.reportPhotoIcon}>🐾</Text></View>}
        <Text style={styles.sectionTitle}>{selectedReport.name} · {selectedReport.species}</Text>
        <Text style={styles.reportMeta}>{selectedReport.status === "resolved" ? "Encontrado" : "Se busca"}</Text>
        <Text style={styles.notificationArea}>⌖ Zona del aviso: {selectedReport.area}</Text>
        <Text style={styles.help}>{selectedReport.description || "No hay señas particulares cargadas."}</Text>
        {reportMapState.status === 'loading' ? <Text accessibilityRole="progressbar" style={styles.help}>Actualizando ubicaciones y avistamientos…</Text> : null}
        {reportMapState.status === 'error' ? <Text style={styles.help}>{reportMapState.error}</Text> : null}
        {selectedReport.search_map ? <SearchMap key={selectedReport.id} data={selectedReport.search_map} resolved={selectedReport.status === 'resolved'}/> : null}
        <Button title="Actualizar avistamientos" variant="outline" disabled={finishingSearch || reportMapState.status === 'loading'} onPress={() => openReport(selectedReport)}/>
        {selectedReport.can_finish_search && reportMapState.status === 'ready' ? <View style={styles.stack}>
          {confirmFound ? <>
            <Text style={styles.help}>¿Confirmás que se encontró a {selectedReport.name}? Se cerrará la búsqueda y se conservarán sus avistamientos. Si solo lo viste, informá un avistamiento.</Text>
            <Button title={finishingSearch ? "Finalizando…" : "Sí, se encontró · Finalizar búsqueda"} disabled={finishingSearch} onPress={finishSearch}/>
            <Button title="Cancelar" variant="outline" disabled={finishingSearch} onPress={() => setConfirmFound(false)}/>
          </> : <Button title="Se encontró · Finalizar búsqueda" onPress={() => setConfirmFound(true)}/>}
        </View> : null}
        {selectedReport.status === "published" ? <Button title="Vi a este animal" onPress={() => { resetSighting(); setScreen("avistamiento"); }}/> : null}
      </View> : null}
      {screen === "avistamiento" && selectedReport ? <View style={styles.stack}>
        <Button title="← Volver al aviso" onPress={() => setScreen("detalle")}/>
        <Text style={styles.sectionTitle}>Informar avistamiento de {selectedReport.name}</Text>
        <Text style={styles.help}>Compartí solo datos reales. La ubicación exacta queda privada y el mapa muestra una zona aproximada.</Text>
        {sightingPhoto?.uri ? <Image source={{uri: sightingPhoto.uri}} style={styles.requestPhoto}/> : <View style={styles.requestPhotoEmpty}><Text style={styles.reportPhotoIcon}>📷</Text><Text style={styles.help}>Una foto ayuda a confirmar el avistamiento</Text></View>}
        <View style={styles.nav}><Button title="Usar cámara" onPress={() => chooseSightingPhoto(true)}/><Button title="Elegir foto" onPress={() => chooseSightingPhoto(false)}/><Button title={sightingLocation ? "Ubicación añadida" : "Usar mi ubicación"} onPress={useSightingLocation}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Zona aproximada</Text><TextInput placeholder="Ej.: Plaza del barrio" placeholderTextColor="#6c8378" value={sightingArea} onChangeText={setSightingArea} style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Qué observaste <Text style={styles.optional}>(opcional)</Text></Text><TextInput placeholder="Dirección en la que iba, compañía, estado..." placeholderTextColor="#6c8378" value={sightingDescription} onChangeText={setSightingDescription} multiline style={[styles.input, styles.textarea]}/></View>
        <Button title="Compartir avistamiento" onPress={submitSighting}/>
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
      {screen === "adopciones" ? <View style={styles.stack}>
        <Text style={styles.sectionTitle}>Adopciones responsables</Text><Text style={styles.help}>Estas publicaciones fueron revisadas por una veterinaria o refugio.</Text>
        <Button title="Publicar para adopción" onPress={() => setScreen("nueva-adopcion")}/>
        {adoptions.length ? adoptions.map(post => <AdoptionCard key={post.id} post={post} onShare={() => shareAdoption(post)} onInterest={() => { setSelectedAdoption(post); setInterestMessage(""); setScreen("interes-adopcion"); }}/>) : <Text style={styles.empty}>Todavía no hay animales publicados para adoptar.</Text>}
      </View> : null}
      {screen === "interes-adopcion" && selectedAdoption ? <View style={styles.stack}><Button title="← Volver a adopciones" onPress={() => setScreen("adopciones")}/><Text style={styles.sectionTitle}>Me interesa adoptar a {selectedAdoption.name}</Text><Text style={styles.help}>Tu mensaje llegará solo a la veterinaria o refugio responsable. Tus datos no se publicarán.</Text><View style={styles.field}><Text style={styles.fieldLabel}>Contanos por qué te interesa</Text><TextInput value={interestMessage} onChangeText={setInterestMessage} multiline placeholder="Ej.: Tengo experiencia, vivo en una casa con patio..." placeholderTextColor="#6c8378" style={[styles.input, styles.textarea]}/></View><Button title="Enviar interés privado" onPress={submitAdoptionInterest}/></View> : null}
      {screen === "mi-actividad" ? <View style={styles.stack}>
        {canManageAdoptions ? <View style={styles.filterRow}>
          <FilterPill active={adoptionAudience === "applicant"} label="Mis solicitudes" onPress={() => setAdoptionAudience("applicant")}/>
          <FilterPill active={adoptionAudience === "institution"} label="Solicitudes recibidas" onPress={() => setAdoptionAudience("institution")}/>
        </View> : null}
        {canManageAdoptions && adoptionAudience === "institution" ? <ShelterInbox api={API} token={token} sessionRequest={sessionRequest} initialData={institutionNotice}/> :
          <AdoptionActivity interests={adoptionInterests} loading={interestsLoading}
            error={interestsError} pendingId={pendingVisitId} onRefresh={() => loadAdoptionInterests()} view={adoptionView} counts={adoptionCounts} onView={loadAdoptionInterests} onArchive={archiveAdoptionInterest}
            onRequest={requestAdoptionVisit} onError={setInterestsError}/>}
      </View> : null}
      {screen === "nueva-adopcion" ? <View style={styles.stack}>
        <Button title="← Volver a adopciones" onPress={() => setScreen("adopciones")}/><Text style={styles.sectionTitle}>Publicar para adopción</Text><Text style={styles.help}>Una veterinaria o refugio responsable revisará la publicación antes de mostrarla.</Text>
        {adoptionPhoto?.uri ? <Image source={{uri: adoptionPhoto.uri}} style={styles.requestPhoto}/> : <View style={styles.requestPhotoEmpty}><Text style={styles.reportPhotoIcon}>🐾</Text><Text style={styles.help}>Agregá una foto clara</Text></View>}
        <View style={styles.nav}><Button title="Usar cámara" onPress={() => selectImage(true, setAdoptionPhoto, "la publicación de adopción")}/><Button title="Elegir foto" onPress={() => selectImage(false, setAdoptionPhoto, "la publicación de adopción")}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Nombre</Text><TextInput value={adoptionName} onChangeText={setAdoptionName} placeholder="Ej.: Mora" placeholderTextColor="#6c8378" style={styles.input}/></View><View style={styles.field}><Text style={styles.fieldLabel}>Especie</Text><TextInput value={adoptionSpecies} onChangeText={setAdoptionSpecies} placeholder="Perro, gato u otro" placeholderTextColor="#6c8378" style={styles.input}/></View><View style={styles.field}><Text style={styles.fieldLabel}>Raza y edad aproximada</Text><TextInput value={adoptionBreed} onChangeText={setAdoptionBreed} placeholder="Ej.: Mestiza" placeholderTextColor="#6c8378" style={styles.input}/><TextInput value={adoptionAge} onChangeText={setAdoptionAge} placeholder="Ej.: 2 años" placeholderTextColor="#6c8378" style={styles.input}/></View><View style={styles.field}><Text style={styles.fieldLabel}>Zona aproximada</Text><TextInput value={adoptionArea} onChangeText={setAdoptionArea} placeholder="Ej.: Barrio Norte" placeholderTextColor="#6c8378" style={styles.input}/></View><View style={styles.field}><Text style={styles.fieldLabel}>Descripción</Text><TextInput value={adoptionDescription} onChangeText={setAdoptionDescription} multiline style={[styles.input, styles.textarea]}/></View><Button title="Enviar para revisión" onPress={submitAdoption}/>
      </View> : null}
      {screen === "veterinaria" ? <View style={styles.stack}>
        <View style={styles.panelIntro}><Text style={styles.sectionKicker}>TU VETERINARIA</Text><Text style={styles.sectionTitle}>La salud de tu familia</Text><Text style={styles.help}>Consultá fichas, historial y accesos familiares en un solo lugar.</Text></View>
        <View style={styles.summaryGrid}>
          <View style={styles.summaryCard}><Text style={styles.summaryValue}>{myAnimals.length}</Text><Text style={styles.summaryLabel}>{myAnimals.length === 1 ? "animal vinculado" : "animales vinculados"}</Text></View>
          <View style={styles.summaryCard}><Text style={styles.summaryValue}>{clinicalRecordCount}</Text><Text style={styles.summaryLabel}>{clinicalRecordCount === 1 ? "registro clínico" : "registros clínicos"}</Text></View>
          <View style={styles.summaryCard}><Text style={styles.summaryValue}>{sharedHistoryCount}</Text><Text style={styles.summaryLabel}>{sharedHistoryCount === 1 ? "historial autorizado" : "historiales autorizados"}</Text></View>
        </View>
        <Button title="＋ Agregar mi animal" onPress={() => { resetNewAnimal(); setScreen("nuevo-animal"); }}/>
        <Button title="Ver todos mis animales" onPress={() => { setScreen("mis-animales"); loadMyAnimals(); }} variant="outline"/>
        {myAnimals.length ? <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Acceso rápido</Text><Text style={styles.help}>Abrí una ficha para consultar su historial clínico y administrar permisos.</Text>{myAnimals.slice(0, 2).map(animal => <Pressable key={animal.id} accessibilityRole="button" onPress={() => openAnimal(animal)} style={({pressed}) => [styles.quickAnimal, pressed && styles.pressed]}>
          {animal.photo_url ? <Image source={{uri: animal.photo_url}} style={styles.quickAnimalAvatar}/> : <View style={styles.quickAnimalPlaceholder}><Text style={styles.animalAvatarText}>{animal.species?.toLowerCase().includes("gato") ? "🐱" : animal.species?.toLowerCase().includes("perro") ? "🐶" : "🐾"}</Text></View>}
          <View style={styles.animalCardContent}><Text style={styles.notificationTitle}>{animal.name}</Text><Text style={styles.notificationArea}>{animal.species}{animal.breed ? ` · ${animal.breed}` : ""}</Text><Text style={styles.animalLink}>Ver ficha e historial →</Text></View>
        </Pressable>)}</View> : <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Tu primera ficha empieza acá</Text><Text style={styles.help}>Agregá a tu animal para tener sus datos organizados cuando necesites atención.</Text></View>}
        <View style={styles.consentCard}><Text style={styles.settingsTitle}>Privacidad de tu historial</Text><Text style={styles.help}>El historial nunca se abre por ubicación. Podés autorizar atención temporal para cada animal desde su ficha, cuando lo necesites.</Text></View>
      </View> : null}
      {screen === "mis-animales" ? <View style={styles.stack}>
        <View style={styles.panelIntro}><Text style={styles.sectionKicker}>TU FAMILIA</Text><Text style={styles.sectionTitle}>Mis animales</Text><Text style={styles.help}>Agregá a tus animales o consultá las fichas que ya están vinculadas a tu cuenta.</Text></View>
        <Button title="＋ Agregar mi animal" onPress={() => { resetNewAnimal(); setScreen("nuevo-animal"); }}/>
        <Button title="⌘ Vincular mascota de mi familia" onPress={() => { setFamilyCode(""); setScreen("vincular-familia"); }} variant="outline"/>
        <Button title="Actualizar mis animales" onPress={() => loadMyAnimals()} variant="outline"/>
        {myAnimals.length ? myAnimals.map(animal => <Pressable key={animal.id} accessibilityRole="button" onPress={() => openAnimal(animal)} style={({pressed}) => [styles.animalCard, pressed && styles.pressed]}>
          {animal.photo_url ? <Image source={{uri: animal.photo_url}} style={styles.animalAvatar}/> : <View style={styles.animalAvatarPlaceholder}><Text style={styles.animalAvatarText}>{animal.species?.toLowerCase().includes("gato") ? "🐱" : animal.species?.toLowerCase().includes("perro") ? "🐶" : "🐾"}</Text></View>}
          <View style={styles.animalCardContent}><Text style={styles.notificationTitle}>{animal.name}</Text><Text style={styles.notificationArea}>{animal.species}{animal.breed ? ` · ${animal.breed}` : ""}</Text><Text style={styles.animalLink}>Ver ficha e historial →</Text></View>
        </Pressable>) : <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Todavía no agregaste animales</Text><Text style={styles.help}>Podés crear su ficha ahora. Luego, una veterinaria podrá completar su atención e historial clínico.</Text></View>}
      </View> : null}
      {screen === "nuevo-animal" ? <View style={styles.stack}>
        <Button title="← Volver a mis animales" onPress={() => setScreen("mis-animales")} variant="outline"/>
        <Text style={styles.sectionTitle}>Agregar mi animal</Text>
        <Text style={styles.help}>La ficha queda vinculada a tu cuenta. Los profesionales solo acceden al historial clínico según los permisos que otorgues.</Text>
        {newAnimalPhoto?.uri ? <Image source={{uri: newAnimalPhoto.uri}} style={styles.requestPhoto}/> : <View style={styles.requestPhotoEmpty}><Text style={styles.reportPhotoIcon}>🐾</Text><Text style={styles.help}>Una foto facilita identificarlo en la atención</Text></View>}
        <View style={styles.nav}><Button title="Usar cámara" onPress={() => selectImage(true, setNewAnimalPhoto, "la ficha de tu animal")}/><Button title="Elegir de galería" onPress={() => selectImage(false, setNewAnimalPhoto, "la ficha de tu animal")}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Nombre</Text><TextInput value={newAnimalName} onChangeText={setNewAnimalName} placeholder="Ej.: Mora" placeholderTextColor="#6c8378" style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Especie</Text><View style={styles.filterRow}><FilterPill active={newAnimalSpecies === "dog"} label="Perro" onPress={() => setNewAnimalSpecies("dog")}/><FilterPill active={newAnimalSpecies === "cat"} label="Gato" onPress={() => setNewAnimalSpecies("cat")}/><FilterPill active={newAnimalSpecies === "other"} label="Otro" onPress={() => setNewAnimalSpecies("other")}/></View></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Raza <Text style={styles.optional}>(opcional)</Text></Text><TextInput value={newAnimalBreed} onChangeText={setNewAnimalBreed} placeholder="Ej.: Mestiza" placeholderTextColor="#6c8378" style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Fecha de nacimiento <Text style={styles.optional}>(opcional)</Text></Text><TextInput value={newAnimalBirthDate} onChangeText={setNewAnimalBirthDate} placeholder="AAAA-MM-DD" placeholderTextColor="#6c8378" style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Microchip o identificación <Text style={styles.optional}>(opcional)</Text></Text><TextInput value={newAnimalMicrochip} onChangeText={setNewAnimalMicrochip} placeholder="Ej.: 981020..." placeholderTextColor="#6c8378" style={styles.input}/></View>
        <View style={styles.field}><Text style={styles.fieldLabel}>Alergias <Text style={styles.optional}>(opcional)</Text></Text><TextInput value={newAnimalAllergies} onChangeText={setNewAnimalAllergies} placeholder="Ej.: Polen, penicilina..." placeholderTextColor="#6c8378" multiline style={[styles.input, styles.textarea]}/></View>
        <Button title="Guardar mi animal" onPress={submitNewAnimal}/>
      </View> : null}
      {screen === "vincular-familia" ? <View style={styles.stack}>
        <Button title="← Volver a mis animales" onPress={() => setScreen("mis-animales")} variant="outline"/>
        <Text style={styles.sectionTitle}>Vincular mascota familiar</Text>
        <Text style={styles.help}>Pedile al responsable de la mascota que genere un código familiar desde su ficha. El código es personal, vence rápido y no crea una mascota duplicada.</Text>
        <View style={styles.field}><Text style={styles.fieldLabel}>Código familiar</Text><TextInput value={familyCode} onChangeText={setFamilyCode} placeholder="Ej.: FAM-ABC..." placeholderTextColor="#6c8378" autoCapitalize="characters" style={styles.input}/></View>
        <Button title="Vincular a mi cuenta" onPress={acceptFamilyInvite}/>
      </View> : null}
      {screen === "mi-animal" && selectedAnimal ? <View style={styles.stack}>
        <Button title="← Volver a mis animales" onPress={() => { setScreen("mis-animales"); loadMyAnimals(); }} variant="outline"/>
        {selectedAnimal.photo_url ? <Image source={{uri: selectedAnimal.photo_url}} style={styles.detailPhoto}/> : <View style={styles.reportPhotoPlaceholder}><Text style={styles.reportPhotoIcon}>{selectedAnimal.species?.toLowerCase().includes("gato") ? "🐱" : selectedAnimal.species?.toLowerCase().includes("perro") ? "🐶" : "🐾"}</Text></View>}
        <Text style={styles.sectionTitle}>{selectedAnimal.name}</Text><Text style={styles.notificationArea}>{selectedAnimal.species}{selectedAnimal.breed ? ` · ${selectedAnimal.breed}` : ""}</Text>
        {selectedAnimal.allergies ? <View style={styles.warningCard}><Text style={styles.warningTitle}>Alergias registradas</Text><Text style={styles.help}>{selectedAnimal.allergies}</Text></View> : null}
        {selectedAnimal.can_share_with_family ? <><View style={styles.consentCard}><Text style={styles.settingsTitle}>Historial compartido durante un viaje</Text><Text style={styles.help}>{selectedAnimal.sharing_enabled ? "Está autorizado. Una veterinaria necesita además tu credencial temporal y localidad coincidente." : "Está desactivado. Ninguna veterinaria puede solicitar el historial temporal hasta que lo autorices."}</Text><Button title={selectedAnimal.sharing_enabled ? "Desactivar historial compartido" : "Autorizar historial compartido"} onPress={() => updateSharingConsent(!selectedAnimal.sharing_enabled)} variant="outline"/></View>
        <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Credencial de viaje</Text><Text style={styles.help}>Genera un código válido por 7 días. Presentalo voluntariamente en la veterinaria de destino; tu GPS nunca abre el historial de forma automática.</Text><Button title="Crear credencial temporal" onPress={createTravelCredential}/><TravelCredentialCard animal={selectedAnimal} credential={travelCredential}/></View></> : null}
        {(selectedAnimal.can_invite_caregiver ?? selectedAnimal.can_share_with_family) ? <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Compartir con familia o cuidadores</Text><Text style={styles.help}>Creá un código temporal para que otra persona de confianza vea la misma ficha, sin duplicar datos ni historial.</Text><Button title="Crear código familiar" onPress={createFamilyInvite}/>{familyInvite?.animalId === selectedAnimal.id ? <View style={styles.credentialCard}><Text style={styles.credentialLabel}>CÓDIGO FAMILIAR · UN SOLO USO</Text><Text selectable style={styles.credentialCode}>{familyInvite.code}</Text><Button title="Copiar código" variant="outline" onPress={() => shareFamilyInvite(true)}/><Button title="Compartir invitación" onPress={() => shareFamilyInvite()}/><Text style={styles.help}>Elegí WhatsApp u otra aplicación para enviarlo.</Text><Text style={styles.help}>Vence {new Date(familyInvite.expires_at).toLocaleString()}. No lo compartas públicamente.</Text></View> : null}{selectedAnimal.family_members?.length ? <View style={styles.familyList}>{selectedAnimal.family_members.map(member => <View key={member.access_id} style={styles.familyMember}><View><Text style={styles.settingsTitle}>{member.name}</Text><Text style={styles.help}>Acceso de consulta activo</Text></View><Button title="Revocar" variant="outline" onPress={() => revokeFamilyAccess(member.access_id, member.name)}/></View>)}</View> : <Text style={styles.help}>Todavía no hay familiares o cuidadores vinculados.</Text>}</View> : <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Acceso familiar</Text><Text style={styles.help}>Esta ficha fue compartida contigo por su responsable. Podés verla junto con su historial, pero solo el titular administra accesos y credenciales.</Text></View>}
        <Text style={styles.sectionTitle}>Historial clínico</Text>{selectedAnimal.clinical_records?.length ? selectedAnimal.clinical_records.map((record, index) => <View key={`${record.date}-${index}`} style={styles.recordCard}><Text style={styles.recordDate}>{new Date(`${record.date}T12:00:00`).toLocaleDateString()}</Text><Text style={styles.settingsTitle}>{record.reason}</Text><Text style={styles.help}>{record.notes}</Text><Text style={styles.recordProfessional}>Registrado por {record.professional}</Text></View>) : <Text style={styles.empty}>Todavía no hay registros clínicos cargados.</Text>}
      </View> : null}
      {screen === "ajustes" ? <View style={styles.stack}>
        <View style={styles.panelIntro}><Text style={styles.sectionKicker}>TU DISPOSITIVO</Text><Text style={styles.sectionTitle}>Mi teléfono y alertas</Text><Text style={styles.help}>Los permisos aparecen solo cuando los necesitás.</Text></View>
        <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Permisos de este dispositivo</Text><Text style={styles.help}>Este estado pertenece a este teléfono y a tu cuenta. Activar un permiso no comparte datos por sí mismo.</Text><PermissionRow icon="⌖" label="Ubicación GPS" status={devicePermissions.location}/><PermissionRow icon="▣" label="Cámara" status={devicePermissions.camera}/><PermissionRow icon="◉" label="Alertas" status={devicePermissions.notifications}/><Button title="Actualizar estado de permisos" onPress={() => syncDevicePermissions()} variant="outline"/></View>
        <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Privacidad y accesos</Text><Text style={styles.help}>La ubicación exacta nunca se publica: el mapa compartido muestra una zona aproximada.</Text><Button title="Compartir mi ubicación" onPress={shareLocation}/><Button title="Probar cámara" onPress={takePhoto} variant="outline"/></View>
        <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Notificaciones</Text><Text style={styles.help}>Recibí novedades de los avisos y solicitudes que seguís.</Text><Button title="Activar alertas en este teléfono" onPress={activatePushNotifications}/><Button title="Ver notificaciones" onPress={() => navigate("notificaciones")} variant="outline"/></View>
        <View style={styles.settingsCard}><Text style={styles.settingsTitle}>Acceso protegido</Text><Text style={styles.help}>{biometricEnabled ? "La huella ya está activa en este teléfono." : "Podés activar la huella para proteger tu sesión."}</Text>{!biometricEnabled ? <Button title="Activar huella" onPress={enableBiometrics} variant="outline"/> : null}</View>
        {photoUri ? <Image source={{uri: photoUri}} style={styles.preview}/> : null}
      </View> : null}
      {screen === "notificaciones" ? <NotificationsInbox api={API} token={token} sessionRequest={sessionRequest}
        onCount={count => { notificationRefresh.current++; setUnreadNotifications(count); }} onOpen={openNotification}/> : null}
    </View>}
      <Text style={styles.message}>{message}</Text>
    </ScrollView>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  notificationsAccess: {flexDirection: "row", alignItems: "center", justifyContent: "center", flexWrap: "wrap", gap: 5, padding: 8, borderRadius: 12, backgroundColor: "#e0f2e9", flexShrink: 1},
  notificationsAccessText: {fontSize: 12, fontWeight: "700", color: "#145c4c"},
  notificationsBadge: {minWidth: 24, height: 24, paddingHorizontal: 4, borderRadius: 12, backgroundColor: "#176b55", alignItems: "center", justifyContent: "center"},
  notificationsBadgeText: {color: "#fff", fontWeight: "800", fontSize: 12},
  screen: {flex: 1, backgroundColor: "#f1fcf8"},
  content: {padding: 16, gap: 16, paddingBottom: 36},
  title: {fontSize: 28, fontWeight: "800", color: "#0d4d42", letterSpacing: -0.6},
  subtitle: {color: "#556864", marginTop: -10},
  stack: {gap: 16},
  field: {gap: 6},
  fieldLabel: {color: "#1d4334", fontSize: 15, fontWeight: "700"},
  optional: {color: "#557267", fontWeight: "400"},
  input: {minHeight: 48, borderWidth: 1, borderColor: "#bfc9c5", backgroundColor: "#f0f4f2", color: "#172d24", borderRadius: 12, padding: 12},
  textarea: {minHeight: 90, textAlignVertical: "top"},
  help: {lineHeight: 20, color: "#466156"},
  sectionTitle: {fontSize: 22, fontWeight: "800", color: "#143f36", marginTop: 1, letterSpacing: -0.35},
  sectionKicker: {fontSize: 11, fontWeight: "800", color: "#0d4d42", letterSpacing: 1.25},
  nav: {flexDirection: "row", flexWrap: "wrap", gap: 8},
  appHeader: {padding: 14, borderRadius: 18, backgroundColor: "#0d4d42", gap: 12, shadowColor: "#00352c", shadowOpacity: 0.16, shadowRadius: 14, elevation: 3},
  appHeaderTop: {minHeight: 42, flexDirection: "row", alignItems: "center", justifyContent: "space-between"},
  brandGroup: {flexDirection: "row", alignItems: "center", gap: 10},
  brandMark: {width: 38, height: 38, borderRadius: 12, backgroundColor: "#b3eedf", alignItems: "center", justifyContent: "center"},
  brandMarkText: {color: "#00352c", fontSize: 21, fontWeight: "900"},
  appBrand: {fontSize: 17, fontWeight: "800", color: "#ffffff"},
  appContext: {fontSize: 11, fontWeight: "800", color: "#b3eedf", textTransform: "uppercase", letterSpacing: 1},
  workspaceSwitcher: {minHeight: 46, padding: 4, borderRadius: 15, flexDirection: "row", backgroundColor: "rgba(229, 240, 237, 0.22)", borderWidth: 1, borderColor: "rgba(179, 238, 223, 0.30)"},
  workspaceOption: {flex: 1, minHeight: 36, alignItems: "center", justifyContent: "center", borderRadius: 11, paddingHorizontal: 10},
  workspaceOptionActive: {backgroundColor: "#ffffff", shadowColor: "#00352c", shadowOpacity: 0.12, shadowRadius: 4, elevation: 2},
  workspaceOptionText: {fontSize: 13, fontWeight: "800", color: "#d1e9e1"},
  workspaceOptionTextActive: {color: "#0d4d42"},
  menuTrigger: {width: 42, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center", backgroundColor: "#e5f0ed"},
  menuTriggerText: {fontSize: 24, lineHeight: 25, color: "#0d4d42", fontWeight: "700"},
  modalScrim: {flex: 1, backgroundColor: "rgba(20, 34, 31, 0.42)", justifyContent: "flex-end"},
  scrimTouch: {flex: 1},
  menuSheet: {backgroundColor: "#ffffff", borderTopLeftRadius: 28, borderTopRightRadius: 28, paddingHorizontal: 18, paddingBottom: 28, paddingTop: 10, gap: 8},
  sheetHandle: {alignSelf: "center", width: 42, height: 4, borderRadius: 3, backgroundColor: "#bfc9c5", marginBottom: 8},
  sheetHeading: {flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 7},
  menuHeading: {fontSize: 18, fontWeight: "800", color: "#143f36"},
  menuSubheading: {fontSize: 13, color: "#556864", marginTop: 2},
  closeButton: {width: 38, height: 38, borderRadius: 19, alignItems: "center", justifyContent: "center", backgroundColor: "#e5f0ed"},
  closeButtonText: {fontSize: 24, lineHeight: 25, color: "#0d4d42"},
  menuItem: {minHeight: 50, borderRadius: 13, flexDirection: "row", alignItems: "center", gap: 13, paddingHorizontal: 13},
  menuItemActive: {backgroundColor: "#e5f0ed"},
  menuIcon: {width: 21, color: "#0d4d42", fontSize: 20, fontWeight: "700", textAlign: "center"},
  menuLabel: {color: "#1b3832", fontSize: 15, fontWeight: "700"},
  menuItemActiveText: {color: "#00352c"},
  menuDangerText: {color: "#93000a"},
  menuDivider: {height: 1, backgroundColor: "#e2ece8", marginVertical: 6},
  pressed: {opacity: 0.72, transform: [{scale: 0.985}]},
  panelIntro: {gap: 4},
  summaryGrid: {flexDirection: "row", gap: 8},
  summaryCard: {flex: 1, minHeight: 94, borderRadius: 16, padding: 12, justifyContent: "space-between", backgroundColor: "#ffffff", borderWidth: 1, borderColor: "#d9e5e1"},
  summaryValue: {fontSize: 27, lineHeight: 31, fontWeight: "900", color: "#0d4d42"},
  summaryLabel: {fontSize: 12, lineHeight: 16, color: "#466156", fontWeight: "700"},
  filterRow: {flexDirection: "row", flexWrap: "wrap", gap: 8},
  filterPill: {minHeight: 40, paddingHorizontal: 15, borderRadius: 22, justifyContent: "center", borderWidth: 1.5, borderColor: "#0d4d42", backgroundColor: "#ffffff"},
  filterPillActive: {backgroundColor: "#0d4d42", borderColor: "#0d4d42"},
  filterPillText: {fontSize: 13, fontWeight: "800", color: "#0d4d42"},
  filterPillTextActive: {color: "#ffffff"},
  button: {minHeight: 48, paddingHorizontal: 18, paddingVertical: 12, alignItems: "center", justifyContent: "center", borderRadius: 24, borderWidth: 1.5},
  buttonPrimary: {backgroundColor: "#0d4d42", borderColor: "#0d4d42"},
  buttonOutline: {backgroundColor: "#ffffff", borderColor: "#0d4d42"},
  buttonDisabled: {opacity: 0.5},
  buttonText: {fontSize: 14, fontWeight: "800"},
  buttonTextPrimary: {color: "#ffffff"},
  buttonTextOutline: {color: "#0d4d42"},
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
  reportCard: {backgroundColor: "#fff", borderWidth: 1, borderColor: "#d9e5e1", borderRadius: 18, overflow: "hidden", shadowColor: "#0d4d42", shadowOpacity: 0.06, shadowRadius: 12, elevation: 2},
  reportPhoto: {width: "100%", height: 280, resizeMode: "cover"},
  reportPhotoPlaceholder: {width: "100%", height: 280, alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: "#e5f0ed"},
  reportPhotoIcon: {fontSize: 52},
  reportPhotoCaption: {color: "#557267"},
  reportContent: {padding: 16, gap: 7},
  animalGlyph: {fontSize: 35},
  adoptionCard: {backgroundColor: "#ffffff", borderRadius: 22, overflow: "hidden", borderWidth: 1, borderColor: "#d6e5df", shadowColor: "#073f35", shadowOpacity: 0.10, shadowRadius: 16, elevation: 3},
  adoptionPhotoFrame: {height: 292, backgroundColor: "#dfeee8", position: "relative"},
  adoptionPhoto: {width: "100%", height: "100%", resizeMode: "cover"},
  adoptionPhotoFallback: {flex: 1, alignItems: "center", justifyContent: "center", gap: 9, backgroundColor: "#dcefe7"},
  adoptionGlyph: {fontSize: 66},
  adoptionFallbackText: {fontSize: 14, fontWeight: "700", color: "#356857"},
  adoptionBadge: {position: "absolute", top: 14, left: 14, backgroundColor: "#fffaf0", borderRadius: 18, paddingHorizontal: 11, paddingVertical: 6, borderWidth: 1, borderColor: "#f4d195"},
  adoptionBadgeText: {fontSize: 10, letterSpacing: 1.1, fontWeight: "900", color: "#875418"},
  adoptionContent: {padding: 17, gap: 9},
  adoptionTitleRow: {flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12},
  adoptionTitleBlock: {flex: 1, gap: 3},
  adoptionName: {fontSize: 25, lineHeight: 29, letterSpacing: -0.45, fontWeight: "900", color: "#123e34"},
  adoptionTraits: {fontSize: 13, fontWeight: "700", color: "#477163"},
  adoptionHeart: {width: 38, height: 38, borderRadius: 19, overflow: "hidden", textAlign: "center", textAlignVertical: "center", fontSize: 25, lineHeight: 38, color: "#0d4d42", backgroundColor: "#e6f5ef"},
  adoptionLocation: {fontSize: 13, fontWeight: "700", color: "#477163"},
  adoptionDescription: {fontSize: 14, lineHeight: 20, color: "#29463f"},
  adoptionOrganization: {flexDirection: "row", alignItems: "center", gap: 8, marginTop: 2},
  organizationMiniMark: {width: 30, height: 30, borderRadius: 15, overflow: "hidden", backgroundColor: "#e5f0ed", alignItems: "center", justifyContent: "center"},
  organizationMiniLogo: {width: 30, height: 30, resizeMode: "cover"},
  organizationMiniLetter: {fontSize: 13, fontWeight: "900", color: "#0d4d42"},
  adoptionOrganizationName: {flex: 1, fontSize: 12, color: "#356857", fontWeight: "700"},
  adoptionCta: {minHeight: 49, marginTop: 3, paddingHorizontal: 17, borderRadius: 24, backgroundColor: "#0d4d42", flexDirection: "row", alignItems: "center", justifyContent: "space-between"},
  adoptionCtaText: {fontSize: 14, fontWeight: "900", color: "#ffffff"},
  adoptionCtaArrow: {fontSize: 21, lineHeight: 22, fontWeight: "700", color: "#b3eedf"},
  organizationLogo: {width: 34, height: 34, borderRadius: 17, resizeMode: "cover", marginBottom: 2},
  organizationName: {fontSize: 13, fontWeight: "700", color: "#326c55", marginTop: 2},
  donationCard: {backgroundColor: "#eef7f2", borderRadius: 12, padding: 11, marginTop: 2},
  donationText: {fontSize: 13, lineHeight: 19, color: "#355f4a"},
  reportMeta: {color: "#147d59", fontWeight: "700"},
  requestPhotoBox: {borderRadius: 14, overflow: "hidden", borderWidth: 1, borderColor: "#cbd9d1", backgroundColor: "#fff"},
  requestPhoto: {width: "100%", height: 280, resizeMode: "cover"},
  detailPhoto: {width: "100%", height: 340, borderRadius: 16, resizeMode: "cover"},
  requestPhotoEmpty: {height: 180, alignItems: "center", justifyContent: "center", gap: 6, padding: 18},
  reviewNote: {color: "#78481e", backgroundColor: "#fff4df", padding: 10, borderRadius: 10},
  settingsCard: {backgroundColor: "#ffffff", borderWidth: 1, borderColor: "#d9e5e1", borderRadius: 16, padding: 16, gap: 11},
  settingsTitle: {fontSize: 16, fontWeight: "800", color: "#143f36"},
  animalCard: {backgroundColor: "#ffffff", borderWidth: 1, borderColor: "#d9e5e1", borderRadius: 18, padding: 12, flexDirection: "row", alignItems: "center", gap: 13, shadowColor: "#0d4d42", shadowOpacity: 0.05, shadowRadius: 8, elevation: 1},
  animalAvatar: {width: 72, height: 72, borderRadius: 18, resizeMode: "cover"},
  animalAvatarPlaceholder: {width: 72, height: 72, borderRadius: 18, backgroundColor: "#e5f0ed", justifyContent: "center", alignItems: "center"},
  animalAvatarText: {fontSize: 36},
  animalCardContent: {flex: 1, gap: 3},
  quickAnimal: {minHeight: 72, flexDirection: "row", alignItems: "center", gap: 11, paddingTop: 10, borderTopWidth: 1, borderTopColor: "#e6efeb"},
  quickAnimalAvatar: {width: 54, height: 54, borderRadius: 14, resizeMode: "cover"},
  quickAnimalPlaceholder: {width: 54, height: 54, borderRadius: 14, backgroundColor: "#e5f0ed", justifyContent: "center", alignItems: "center"},
  animalLink: {fontSize: 13, fontWeight: "800", color: "#0d4d42", marginTop: 3},
  consentCard: {backgroundColor: "#eaf7f1", borderWidth: 1, borderColor: "#a8dfcb", borderRadius: 16, padding: 16, gap: 11},
  warningCard: {backgroundColor: "#fff4df", borderWidth: 1, borderColor: "#f1cf9b", borderRadius: 14, padding: 14, gap: 5},
  warningTitle: {fontSize: 14, fontWeight: "800", color: "#754b17"},
  travelCredentialCard: {marginTop: 4, borderRadius: 20, padding: 16, gap: 14, backgroundColor: "#0d4d42", overflow: "hidden", shadowColor: "#00352c", shadowOpacity: 0.16, shadowRadius: 12, elevation: 3},
  credentialTopBar: {flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between"},
  credentialOverline: {fontSize: 10, fontWeight: "900", letterSpacing: 1.25, color: "#b3eedf"},
  credentialHeading: {fontSize: 19, fontWeight: "900", color: "#ffffff", marginTop: 3},
  credentialSeal: {width: 38, height: 38, borderRadius: 19, alignItems: "center", justifyContent: "center", backgroundColor: "#b3eedf"},
  credentialSealText: {fontSize: 21, fontWeight: "900", color: "#00352c"},
  credentialAnimalRow: {flexDirection: "row", alignItems: "center", gap: 12},
  credentialAnimalPhoto: {width: 68, height: 68, borderRadius: 18, resizeMode: "cover", borderWidth: 2, borderColor: "#b3eedf"},
  credentialAnimalFallback: {width: 68, height: 68, borderRadius: 18, backgroundColor: "#e5f0ed", alignItems: "center", justifyContent: "center"},
  credentialAnimalInfo: {flex: 1, gap: 2},
  credentialAnimalName: {fontSize: 22, fontWeight: "900", color: "#ffffff"},
  credentialAnimalMeta: {fontSize: 12, lineHeight: 17, color: "#d2ebe3"},
  credentialCodePanel: {borderRadius: 14, backgroundColor: "#ffffff", paddingVertical: 13, paddingHorizontal: 12, alignItems: "center", gap: 4},
  credentialExpires: {fontSize: 12, color: "#466156", textAlign: "center"},
  credentialFootnote: {fontSize: 11, lineHeight: 16, color: "#c7e4db", textAlign: "center"},
  credentialCard: {backgroundColor: "#e5f0ed", borderRadius: 13, padding: 14, gap: 5, alignItems: "center"},
  credentialLabel: {fontSize: 11, fontWeight: "900", letterSpacing: 1.2, color: "#326c55"},
  credentialCode: {fontSize: 19, fontWeight: "900", color: "#00352c", letterSpacing: 1.4, textAlign: "center"},
  familyList: {gap: 8, marginTop: 2},
  familyMember: {paddingTop: 10, borderTopWidth: 1, borderTopColor: "#dbe7df", flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12},
  recordCard: {backgroundColor: "#ffffff", borderWidth: 1, borderColor: "#d9e5e1", borderRadius: 15, padding: 15, gap: 6},
  recordDate: {fontSize: 12, fontWeight: "800", color: "#326c55", textTransform: "uppercase"},
  recordProfessional: {fontSize: 12, color: "#557267", marginTop: 2},
  permissionRow: {minHeight: 42, flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 5, borderBottomWidth: 1, borderBottomColor: "#edf3f1"},
  permissionIcon: {width: 22, textAlign: "center", fontSize: 18, color: "#0d4d42"},
  permissionLabel: {flex: 1, fontSize: 14, fontWeight: "700", color: "#29463f"},
  permissionStatus: {paddingHorizontal: 9, paddingVertical: 4, borderRadius: 12, overflow: "hidden", fontSize: 11, fontWeight: "800", color: "#556864", backgroundColor: "#edf3f1"},
  permissionGranted: {color: "#00352c", backgroundColor: "#b3eedf"},
  permissionDenied: {color: "#93000a", backgroundColor: "#ffdad6"},
});
