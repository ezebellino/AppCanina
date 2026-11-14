import React, {useEffect, useRef} from 'react';
import {AccessibilityInfo, Animated, Pressable, StyleSheet, Text, View} from 'react-native';

const titles = {found: '¡Volvió a casa!', sent: 'Solicitud enviada', family: 'Ahora lo cuidan juntos', visit: 'Visita aceptada'};
const details = {found: 'La búsqueda quedó finalizada.', sent: 'Podés seguirla en Mis solicitudes.', family: 'Comparten la misma ficha e historial.', visit: 'Revisá el día, horario y las indicaciones.'};

function useProgress(play) {
  const progress = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    let active = true;
    const finish = () => {progress.stopAnimation(); progress.setValue(1);};
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', reduced => {if (reduced) finish();});
    if (play) AccessibilityInfo.isReduceMotionEnabled().then(reduced => {
      if (!active || reduced) return;
      progress.setValue(0);
      Animated.timing(progress, {toValue: 1, duration: 700, useNativeDriver: true}).start();
    }).catch(() => {});
    return () => {active = false; subscription.remove(); progress.stopAnimation();};
  }, [play, progress]);
  return progress;
}

function Paw() {
  return <View style={styles.paw}><View style={styles.pawPad}/>{[0, 1, 2, 3].map(i => <View key={i} style={[styles.toe, {left: i * 12, top: i === 0 || i === 3 ? 12 : 1}]}/>)}</View>;
}
function Person({style}) {
  return <Animated.View style={[styles.person, style]}><View style={styles.head}/><View style={styles.body}/></Animated.View>;
}

export function VisitReveal({eventKey, children, style}) {
  const progress = useProgress(eventKey);
  return <Animated.View style={[style, {opacity: progress.interpolate({inputRange: [0, 1], outputRange: [.4, 1]}),
    transform: [{translateY: progress.interpolate({inputRange: [0, 1], outputRange: [10, 0]})}]}]}>{children}</Animated.View>;
}

export default function SuccessMotion({kind, onDismiss}) {
  const progress = useProgress(kind);
  if (!titles[kind]) return null;
  const scale = progress.interpolate({inputRange: [0, .7, 1], outputRange: [.6, 1.05, 1]});
  return <View style={styles.banner} accessibilityLiveRegion="polite">
    <View style={styles.art} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {kind === 'family' ? <>
        <Person style={{left: 0, transform: [{translateX: progress.interpolate({inputRange: [0, 1], outputRange: [-14, 0]})}]}}/>
        <Person style={{right: 0, transform: [{translateX: progress.interpolate({inputRange: [0, 1], outputRange: [14, 0]})}]}}/>
        <Animated.View style={[styles.familyPaw, {transform: [{scale}]}]}><Paw/></Animated.View>
      </> : <Animated.View style={{transform: [{scale}, {translateX: progress.interpolate({inputRange: [0, 1], outputRange: [kind === 'sent' ? -20 : 0, 0]})}]}}>
        {kind === 'found' ? <Paw/> : kind === 'sent' ? <View style={styles.envelope}><View style={styles.flap}/></View> : <View style={styles.calendar}><View style={styles.calendarBar}/><Text style={styles.dots}>• • •</Text></View>}
      </Animated.View>}
      <Animated.View style={[styles.check, {opacity: progress, transform: [{scale}]}]}><Text style={styles.checkText}>✓</Text></Animated.View>
    </View>
    <View style={styles.copy}><Text style={styles.title}>{titles[kind]}</Text><Text style={styles.detail}>{details[kind]}</Text></View>
    <Pressable accessibilityRole="button" accessibilityLabel="Cerrar confirmación" onPress={onDismiss} style={styles.close}><Text style={styles.closeText}>×</Text></Pressable>
  </View>;
}
const styles = StyleSheet.create({
  banner: {backgroundColor: '#e8f6ef', borderColor: '#a8d3bd', borderWidth: 1, borderRadius: 16, margin: 12, padding: 12, flexDirection: 'row', alignItems: 'center', gap: 10},
  art: {width: 68, height: 66, justifyContent: 'center', alignItems: 'center'},
  copy: {flex: 1}, title: {fontSize: 16, fontWeight: '800', color: '#164e41'}, detail: {fontSize: 13, lineHeight: 18, color: '#355f4a', marginTop: 4},
  close: {minWidth: 44, minHeight: 44, justifyContent: 'center', alignItems: 'center'}, closeText: {fontSize: 26, color: '#164e41'},
  paw: {width: 52, height: 55}, pawPad: {position: 'absolute', left: 9, top: 25, width: 34, height: 27, borderRadius: 14, backgroundColor: '#176b55'},
  toe: {position: 'absolute', width: 12, height: 18, borderRadius: 7, backgroundColor: '#176b55'},
  check: {position: 'absolute', right: 0, bottom: 0, width: 27, height: 27, borderRadius: 14, borderWidth: 2, borderColor: '#e8f6ef', backgroundColor: '#176b55', alignItems: 'center', justifyContent: 'center'}, checkText: {color: '#fff', fontSize: 18, fontWeight: '800'},
  envelope: {width: 54, height: 40, borderRadius: 6, borderWidth: 2, borderColor: '#176b55', backgroundColor: '#fff', overflow: 'hidden'}, flap: {width: 38, height: 38, backgroundColor: '#b5dec9', position: 'absolute', top: -21, left: 6, transform: [{rotate: '45deg'}]},
  calendar: {width: 50, height: 48, borderWidth: 2, borderColor: '#176b55', borderRadius: 7, backgroundColor: '#fff', overflow: 'hidden'}, calendarBar: {height: 12, backgroundColor: '#b5dec9', borderBottomWidth: 2, borderColor: '#176b55'}, dots: {fontSize: 22, color: '#176b55', textAlign: 'center'},
  person: {position: 'absolute', top: 4, width: 26, alignItems: 'center'}, head: {width: 17, height: 17, borderRadius: 9, backgroundColor: '#176b55'}, body: {width: 26, height: 22, borderTopLeftRadius: 14, borderTopRightRadius: 14, backgroundColor: '#176b55', marginTop: 4},
  familyPaw: {position: 'absolute', top: 27, left: 13, width: 42, height: 34, alignItems: 'center', borderRadius: 18, backgroundColor: '#e8f6ef'},
});
