import React, {useMemo, useState} from 'react';
import {Linking, Pressable, StyleSheet, Text, View} from 'react-native';
import {WebView} from 'react-native-webview';
import {mapHtml, mapsUrl, searchRegion} from './search-map.cjs';

const date = value => {
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) ? parsed.toLocaleString() : 'Fecha no disponible';
};

export default function SearchMap({data, resolved}) {
  const [error, setError] = useState('');
  const [showMap, setShowMap] = useState(false);
  const region = useMemo(() => searchRegion(data), [data]);
  const html = useMemo(() => mapHtml(data), [data]);
  const latest = data?.latest_observation;
  const lastMapped = region.points[0];
  const url = mapsUrl(data?.points?.find(p => mapsUrl(p)));
  const openMaps = async () => {
    try { if (url) await Linking.openURL(url); }
    catch { setError('No se pudo abrir Maps. Revisá la conexión e intentá nuevamente.'); }
  };
  return <View style={styles.card}>
    <Text style={styles.title}>{resolved ? 'Ubicaciones reportadas' : 'Dónde buscar'}</Text>
    <Text style={styles.label}>Último reporte: {latest?.area || 'Zona no informada'}</Text>
    <Text style={styles.help}>{date(latest?.seen_at)}</Text>
    {!lastMapped ? <Text style={styles.help}>Todavía no hay coordenadas para mostrar un mapa. Podés guiarte por la zona indicada o aportar un avistamiento.</Text> : <>
      {!mapsUrl(latest) ? <Text style={styles.help}>El último reporte no tiene coordenadas. El mapa usa la última ubicación disponible: {lastMapped.area} · {date(lastMapped.seen_at)}.</Text> : null}
      <Pressable accessibilityRole="button" style={styles.button} onPress={openMaps}><Text style={styles.buttonText}>Abrir última ubicación en Maps</Text></Pressable>
      <Text style={styles.help}>El punto es aproximado, no una dirección exacta. Abrir Maps comparte ese punto con Google Maps.</Text>
      <Text style={styles.label}>{region.points.length > 1 ? 'Zona estimativa de búsqueda' : 'Zona del único punto disponible'}</Text>
      <Text style={styles.help}>{region.points.length} punto{region.points.length === 1 ? '' : 's'} con coordenadas entre los últimos 20 reportes. Desde {date(region.points[region.points.length - 1].seen_at)} hasta {date(lastMapped.seen_at)}.</Text>
      <Text style={styles.help}>El área abarca ubicaciones aproximadas reportadas; no predice dónde está el animal ni confirma los avistamientos.</Text>
      {region.radius > 10000 ? <Text style={styles.help}>Los puntos están muy separados. Revisá las fechas y cada reporte antes de organizar la búsqueda.</Text> : null}
      {showMap ? <WebView source={{html}} style={styles.map} originWhitelist={['*']}
        applicationNameForUserAgent="Lazuna community search map"
        onShouldStartLoadWithRequest={request => request.url === 'about:blank' || request.url === 'about:srcdoc'}
        javaScriptCanOpenWindowsAutomatically={false} setSupportMultipleWindows={false}
        allowFileAccess={false} allowUniversalAccessFromFileURLs={false} mixedContentMode="never"
        geolocationEnabled={false} sharedCookiesEnabled={false} thirdPartyCookiesEnabled={false}
        onError={() => setError('No se pudo cargar el mapa. Podés usar el botón de Maps.')}
        onMessage={event => { if (event.nativeEvent.data === 'error') setError('No se pudo cargar el mapa. Podés usar el botón de Maps.'); }}
      /> : <Pressable accessibilityRole="button" style={styles.button} onPress={() => setShowMap(true)}><Text style={styles.buttonText}>Mostrar mapa y zona aproximada</Text></Pressable>}
      <Pressable accessibilityRole="link" onPress={() => Linking.openURL('https://www.openstreetmap.org/copyright').catch(() => setError('No se pudo abrir la información del mapa.'))}><Text style={styles.help}>Mapa © OpenStreetMap contributors</Text></Pressable>
      <Text style={styles.help}>Requiere conexión; no solicita tu ubicación.</Text>
    </>}
    {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
  </View>;
}
const styles = StyleSheet.create({
  card: {backgroundColor: '#fff', borderRadius: 18, padding: 16, gap: 12},
  title: {fontSize: 20, fontWeight: '800', color: '#183e2d'},
  label: {fontSize: 16, fontWeight: '700', color: '#234b38'},
  help: {fontSize: 14, lineHeight: 20, color: '#486251'},
  button: {padding: 14, borderRadius: 12, backgroundColor: '#236c49', alignItems: 'center'},
  buttonText: {color: '#fff', fontWeight: '700', textAlign: 'center'},
  map: {height: 320, flex: 0, backgroundColor: '#edf4ef'},
  error: {color: '#9c3026', fontSize: 14},
});
