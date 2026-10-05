import React, {useState} from "react";
import {Button, Image, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View} from "react-native";
import * as SecureStore from "expo-secure-store";
import * as Location from "expo-location";
import * as ImagePicker from "expo-image-picker";

const API = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/extraviados/api/v1";

export default function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("Ingresá para colaborar.");
  const [photoUri, setPhotoUri] = useState("");
  const [notifications, setNotifications] = useState([]);

  const loadNotifications = async (accessToken = token) => {
    const response = await fetch(`${API}/notificaciones/`, {headers: {Authorization: `Bearer ${accessToken}`}});
    const data = await response.json();
    if (!response.ok) throw Error(data.detail || "No se pudieron consultar las notificaciones.");
    setNotifications(data.notifications);
    setMessage(data.notifications.length ? `${data.notifications.length} notificación${data.notifications.length === 1 ? "" : "es"} pendiente${data.notifications.length === 1 ? "" : "s"}.` : "No hay notificaciones pendientes.");
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

  return <SafeAreaView style={styles.screen}>
    <ScrollView contentContainerStyle={styles.content}>
      <Text style={styles.title}>Tu Veterinaria</Text>
      <Text style={styles.subtitle}>Comunidad · animales extraviados</Text>
      {!token ? <View style={styles.stack}>
      <TextInput placeholder="Usuario" value={username} onChangeText={setUsername} autoCapitalize="none" style={styles.input}/>
      <TextInput placeholder="Contraseña" value={password} onChangeText={setPassword} secureTextEntry style={styles.input}/>
      <Button title="Ingresar" onPress={login}/>
    </View> : <View style={styles.stack}>
      <Text style={styles.help}>Cuando publiques un aviso podrás elegir si querés compartir tu ubicación o una foto. Nada se solicita por adelantado.</Text>
      <Button title="⌖ Compartir mi ubicación" onPress={shareLocation}/>
      <Button title="▣ Usar cámara" onPress={takePhoto}/>
      <Button title="Actualizar notificaciones" onPress={() => loadNotifications()}/>
      {photoUri ? <Image source={{uri: photoUri}} style={styles.preview}/> : null}
      {notifications.map(notification => <View key={notification.id} style={styles.notificationCard}>
        {notification.photo_url ? <Image source={{uri: notification.photo_url}} style={styles.notificationPhoto}/> : null}
        <View style={styles.notificationContent}>
          <Text style={styles.notificationTitle}>{notification.title}</Text>
          <Text style={styles.notificationAnimal}>{notification.animal_name} · {notification.species}</Text>
          <Text style={styles.notificationArea}>⌖ {notification.area}</Text>
          <Text>{notification.description || notification.body}</Text>
        </View>
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
  input: {borderWidth: 1, borderColor: "#cbd9d1", backgroundColor: "#fff", borderRadius: 10, padding: 12},
  help: {lineHeight: 20, color: "#466156"},
  message: {lineHeight: 21, color: "#213a30"},
  preview: {width: "100%", height: 220, borderRadius: 12, resizeMode: "cover"},
  notificationCard: {backgroundColor: "#fff", borderWidth: 1, borderColor: "#dbe7df", borderRadius: 14, overflow: "hidden"},
  notificationPhoto: {width: "100%", height: 180, resizeMode: "cover"},
  notificationContent: {padding: 14, gap: 4},
  notificationTitle: {fontSize: 17, fontWeight: "700", color: "#1d4334"},
  notificationAnimal: {fontWeight: "600", color: "#355f4a"},
  notificationArea: {color: "#557267"},
});
