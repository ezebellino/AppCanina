import React, {useState} from "react";
import {Button, SafeAreaView, Text, TextInput, View} from "react-native";
import * as SecureStore from "expo-secure-store";

const API = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/extraviados/api/v1";

export default function App() {
  const [username, setUsername] = useState(""); const [password, setPassword] = useState(""); const [token, setToken] = useState(""); const [message, setMessage] = useState("Ingresá para colaborar.");
  const login = async () => { try { const r = await fetch(`${API}/sesion/`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({username,password,device_name:"App móvil"})}); const data=await r.json(); if(!r.ok) throw Error(data.detail); await SecureStore.setItemAsync("community-token",data.token); setToken(data.token); setMessage(`Sesión iniciada: ${data.user.username}`); } catch(e) { setMessage(e.message); }};
  const notifications = async () => { const r=await fetch(`${API}/notificaciones/`,{headers:{Authorization:`Bearer ${token}`}}); const d=await r.json(); setMessage(r.ok ? (d.notifications.length ? d.notifications.map(n=>n.title).join("\n") : "Sin notificaciones pendientes.") : d.detail); };
  return <SafeAreaView style={{flex:1,padding:24,gap:14}}><Text style={{fontSize:26,fontWeight:"700"}}>Tu Veterinaria</Text><Text>Comunidad · animales extraviados</Text>{!token ? <><TextInput placeholder="Usuario" value={username} onChangeText={setUsername} autoCapitalize="none" style={{borderWidth:1,padding:12}}/><TextInput placeholder="Contraseña" value={password} onChangeText={setPassword} secureTextEntry style={{borderWidth:1,padding:12}}/><Button title="Ingresar" onPress={login}/></> : <Button title="Ver notificaciones" onPress={notifications}/>}<Text>{message}</Text></SafeAreaView>;
}
