import React, {useState} from "react";
import {Button, Image, SafeAreaView, StyleSheet, Text, TextInput, View} from "react-native";
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

  const notifications = async () => {
    const response = await fetch(`${API}/notificaciones/`, {headers: {Authorization: `Bearer ${token}`}});
    const data = await response.json();
    setMessage(response.ok ? (data.notifications.length ? data.notifications.map(notification => notification.title).join("\n") : "Sin notificaciones pendientes.") : data.detail);
  };

  return <SafeAreaView style={styles.screen}>
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
      <Button title="Ver notificaciones" onPress={notifications}/>
      {photoUri ? <Image source={{uri: photoUri}} style={styles.preview}/> : null}
    </View>}
    <Text style={styles.message}>{message}</Text>
  </SafeAreaView>;
}

const styles = StyleSheet.create({
  screen: {flex: 1, padding: 24, gap: 12, backgroundColor: "#f7faf8"},
  title: {fontSize: 26, fontWeight: "700", color: "#1d4334"},
  subtitle: {color: "#557267"},
  stack: {gap: 12},
  input: {borderWidth: 1, borderColor: "#cbd9d1", backgroundColor: "#fff", borderRadius: 10, padding: 12},
  help: {lineHeight: 20, color: "#466156"},
  message: {lineHeight: 21, color: "#213a30"},
  preview: {width: "100%", height: 220, borderRadius: 12, resizeMode: "cover"},
});
