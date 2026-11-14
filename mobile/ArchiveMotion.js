import React, {useEffect, useRef} from 'react';
import {AccessibilityInfo, Animated, StyleSheet, Text, View} from 'react-native';

// Called only after the server confirms an archive. No dependencies or native build setup.
export default function ArchiveMotion({children, style}) {
  const fold = useRef(new Animated.Value(0)).current;
  const travel = useRef(new Animated.Value(0)).current;
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; fold.stopAnimation(); travel.stopAnimation(); }, []);
  const animate = async () => {
    try {
      if (await AccessibilityInfo.isReduceMotionEnabled() || !alive.current) return;
      await new Promise(resolve => Animated.sequence([
        Animated.timing(fold, {toValue: 1, duration: 280, useNativeDriver: true}),
        Animated.timing(travel, {toValue: 1, duration: 500, useNativeDriver: true}),
      ]).start(resolve));
    } catch { /* Motion must never block a confirmed archive. */ }
  };
  return <View style={styles.wrapper}>
    <Animated.View style={[style, {opacity: fold.interpolate({inputRange: [0, 1], outputRange: [1, 0]}),
      transform: [{scaleY: fold.interpolate({inputRange: [0, 1], outputRange: [1, .12]})},
        {scaleX: fold.interpolate({inputRange: [0, 1], outputRange: [1, .6]})}]}]}>
      {children(animate)}
    </Animated.View>
    <Animated.View pointerEvents="none" accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={[styles.tray, {opacity: fold}]}>
      <View style={styles.slot}/><Text style={styles.label}>Archivadas</Text>
    </Animated.View>
    <Animated.View pointerEvents="none" accessibilityElementsHidden importantForAccessibility="no-hide-descendants" style={[styles.envelope, {
      opacity: Animated.multiply(fold, travel.interpolate({inputRange: [0, .85, 1], outputRange: [1, 1, 0]})),
      transform: [{translateY: travel.interpolate({inputRange: [0, 1], outputRange: [-90, 25]})},
        {scale: travel.interpolate({inputRange: [0, 1], outputRange: [1, .2]})},
        {rotate: travel.interpolate({inputRange: [0, .5, 1], outputRange: ['-8deg', '8deg', '0deg']})}],
    }]}><View style={styles.flap}/></Animated.View>
  </View>;
}
const styles = StyleSheet.create({
  wrapper: {position: 'relative'},
  envelope: {position: 'absolute', bottom: 55, right: 32, width: 80, height: 54, borderWidth: 2, borderColor: '#176b55', borderRadius: 7, backgroundColor: '#f0faf4', overflow: 'hidden'},
  flap: {position: 'absolute', top: -30, left: 10, width: 56, height: 56, backgroundColor: '#b5dec9', transform: [{rotate: '45deg'}], borderRadius: 4},
  tray: {position: 'absolute', bottom: 15, right: 12, width: 120, padding: 12, borderRadius: 12, backgroundColor: '#176b55', gap: 8},
  slot: {height: 5, borderRadius: 3, backgroundColor: '#0d3d30'},
  label: {color: '#fff', fontWeight: '700', textAlign: 'center'},
});
