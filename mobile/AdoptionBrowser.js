import React, {useEffect, useRef, useState} from 'react';
import {View, Text, TextInput, Pressable, ScrollView, StyleSheet, ActivityIndicator} from 'react-native';
import * as Location from 'expo-location';

const empty = {q: '', locality: '', shelter: '', species: '', radius: '', lat: '', lon: ''};
export default function AdoptionBrowser({request, api, token, renderItem, initialFilters = empty, onApplied}) {
  const [filters, setFilters] = useState(initialFilters);
  const [applied, setApplied] = useState(initialFilters);
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [locationNote, setLocationNote] = useState('Sin ubicación: primero las publicaciones recientes.');
  const [choosing, setChoosing] = useState(false);
  const sequence = useRef(0);
  const locationSequence = useRef(0);
  const set = (key, value) => setFilters(old => ({...old, [key]: value}));
  async function load(next = filters, page = 1) {
    const id = ++sequence.current;
    setBusy(true); setError('');
    try {
      const params = Object.entries({...next, page}).filter(([,v]) => v !== '').map(([k,v]) => `${k}=${encodeURIComponent(v)}`).join('&');
      const response = await request(`${api}/adopciones/?${params}`, {headers: {Authorization: `Bearer ${token}`}});
      const result = await response.json();
      if (!response.ok) throw Error(result.errors ? Object.values(result.errors).flat().join(' ') : result.detail || 'No se pudieron cargar las adopciones.');
      if (id !== sequence.current) return;
      setData(result); setApplied(next); onApplied?.(next);
    } catch (e) { if (id === sequence.current) setError(e.message); }
    finally { if (id === sequence.current) setBusy(false); }
  }
  useEffect(() => { load(initialFilters); return () => {sequence.current++; locationSequence.current++;}; }, []);
  async function locate() {
    const id = ++locationSequence.current;
    setLocationNote('Obteniendo ubicación…');
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== 'granted') throw Error('Podés continuar por localidad sin activar la ubicación.');
      let timer;
      let position;
      try {
        position = await Promise.race([
          Location.getCurrentPositionAsync({accuracy: Location.Accuracy.Balanced}),
          new Promise((_, reject) => {timer = setTimeout(() => reject(Error('La ubicación tardó demasiado. Podés buscar por localidad.')), 15000);}),
        ]);
      } finally { clearTimeout(timer); }
      if (id !== locationSequence.current) return;
      setFilters(old => ({...old, lat: position.coords.latitude.toFixed(2), lon: position.coords.longitude.toFixed(2)}));
      setLocationNote('Ubicación aproximada lista. Aplicá los filtros para ordenar por cercanía.');
    } catch (e) { if (id === locationSequence.current) setLocationNote(e.message || 'No pudimos obtener la ubicación. Podés buscar por localidad.'); }
  }
  const action = (label, onPress, active = false, disabled = false, key = label) => <Pressable key={key} accessibilityRole="button" accessibilityState={{selected: active, disabled}} disabled={disabled} onPress={onPress} style={[s.button, active && s.active, disabled && {opacity: .5}]}><Text style={[s.buttonText, active && {color: '#fff'}]}>{label}</Text></Pressable>;
  return <View style={s.stack}>
    <View style={s.panel}>
      <Text style={s.title}>Encontrá a tu próximo compañero</Text>
      <Text>Nombre o raza</Text><TextInput accessibilityLabel="Nombre o raza" style={s.input} value={filters.q} onChangeText={v => set('q', v)} maxLength={100}/>
      <Text>Localidad del animal</Text><TextInput accessibilityLabel="Localidad del animal" placeholder="Ej.: Avellaneda" style={s.input} value={filters.locality} onChangeText={v => set('locality', v)} maxLength={120}/>
      <View style={s.row}>{[['', 'Todas las especies'], ['dog', 'Perros'], ['cat', 'Gatos'], ['other', 'Otros']].map(([value, label]) => action(label, () => set('species', value), filters.species === value))}</View>
      {action(data?.shelters?.find(x => String(x.id) === filters.shelter)?.name || 'Todos los refugios', () => setChoosing(!choosing))}
      {choosing && <ScrollView style={{maxHeight: 200}} nestedScrollEnabled>{action('Todos los refugios', () => {set('shelter', ''); setChoosing(false);})}{data?.shelters?.map(org => action(`${org.name} · ${org.locality || 'Localidad sin informar'}`, () => {set('shelter', String(org.id)); setChoosing(false);}, false, false, String(org.id)))}</ScrollView>}
      <Text>Distancia desde mi ubicación</Text>
      <View style={s.row}>{['', '10', '25', '50', '100'].map(n => action(n ? `${n} km` : 'Sin límite', () => set('radius', n), filters.radius === n))}</View>
      <Text accessibilityLiveRegion="polite">{locationNote}</Text>
      <View style={s.row}>{action('Mi ubicación', locate)}{action('Quitar ubicación', () => {locationSequence.current++; setFilters(old => ({...old, lat: '', lon: '', radius: ''})); setLocationNote('Ubicación quitada. Podés buscar por localidad.');})}</View>
      <View style={s.row}>{action('Aplicar filtros', () => load(), true, busy)}{action('Limpiar', () => {locationSequence.current++; setFilters(empty); setLocationNote('Sin ubicación: primero las publicaciones recientes.'); load(empty);}, false, busy)}</View>
    </View>
    {busy && <ActivityIndicator accessibilityLabel="Buscando adopciones"/>}
    {!!error && <Text accessibilityRole="alert">{error} Los resultados anteriores conservan sus filtros.</Text>}
    {data && <Text>{data.total} resultados · Página {data.page}. {applied.radius ? `Hasta ${applied.radius} km. ${data.missing_locations} publicaciones sin ubicación quedan fuera del radio.` : 'Sin límite de distancia.'} Distancias aproximadas en línea recta.</Text>}
    {data?.adoptions?.map(renderItem)}
    {data && !data.adoptions.length && <Text>No hay resultados. Probá otra localidad o refugio, o ampliá la distancia.</Text>}
    {!!applied.radius && action('Buscar sin límite de distancia', () => {const next = {...applied, radius: ''}; setFilters(next); load(next);}, false, busy)}
    <View style={s.row}>{data?.page > 1 && action('Anterior', () => load(applied, data.page - 1), false, busy)}{data?.has_next && action('Siguiente', () => load(applied, data.page + 1), false, busy)}</View>
  </View>;
}
const s = StyleSheet.create({stack: {gap: 14}, panel: {backgroundColor: '#fff', borderRadius: 18, padding: 16, gap: 10}, title: {fontSize: 19, fontWeight: '700', color: '#075448'}, input: {borderWidth: 1, borderColor: '#b8cec5', borderRadius: 10, padding: 12, color: '#153e35'}, row: {flexDirection: 'row', flexWrap: 'wrap', gap: 8}, button: {borderWidth: 1, borderColor: '#075448', padding: 12, borderRadius: 20, marginVertical: 2}, active: {backgroundColor: '#075448'}, buttonText: {color: '#075448', fontWeight: '700'}});
