import React, {useState} from 'react';
import {View, Text, Pressable, StyleSheet} from 'react-native';
import * as Clipboard from 'expo-clipboard';

export default function ShelterDonation({organization}) {
  const [message, setMessage] = useState('');
  if (!organization?.donation_alias) return null;
  async function copy() {
    try {
      const copied = await Clipboard.setStringAsync(organization.donation_alias);
      setMessage(copied === false ? 'No pudimos copiarlo. Seleccioná el alias para copiarlo manualmente.' : 'Alias copiado. Ya podés pegarlo en tu banco o billetera.');
    } catch {
      setMessage('No pudimos copiarlo. Seleccioná el alias para copiarlo manualmente.');
    }
  }
  return <View style={styles.card}>
    <Text style={styles.title}>Colaborá con {organization.name}</Text>
    <Text style={styles.text}>{organization.donation_message || 'Tu aporte ayuda a cuidar a los animales del refugio.'}</Text>
    <Text style={styles.text}>Alias para transferencias</Text>
    <Text selectable style={styles.alias}>{organization.donation_alias}</Text>
    <Pressable accessibilityRole="button" accessibilityLabel={`Copiar alias de ${organization.name}`} onPress={copy} style={styles.button}><Text style={styles.title}>Copiar alias</Text></Pressable>
    {message ? <Text accessibilityLiveRegion="polite" style={styles.text}>{message}</Text> : null}
    <Text style={styles.text}>Colaboración voluntaria, independiente de la adopción. Verificá el destinatario en tu banco antes de transferir.</Text>
  </View>;
}
const styles = StyleSheet.create({
  card: {backgroundColor: '#eef7f2', borderRadius: 12, padding: 14, gap: 8},
  title: {fontSize: 15, fontWeight: '700', color: '#164e41'},
  text: {fontSize: 13, lineHeight: 19, color: '#355f4a'},
  alias: {fontSize: 17, fontWeight: '700', color: '#164e41'},
  button: {minHeight: 44, padding: 10, borderRadius: 8, borderWidth: 1, borderColor: '#357663', alignSelf: 'flex-start', justifyContent: 'center'},
});
