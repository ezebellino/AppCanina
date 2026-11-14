import React, {useEffect, useRef, useState} from 'react';
import {AccessibilityInfo, Animated, Modal, Pressable, ScrollView, StyleSheet, View} from 'react-native';
import {SafeAreaProvider, SafeAreaView} from 'react-native-safe-area-context';

export default function MenuMotion({visible, onClose, children}) {
  const [mounted, setMounted] = useState(visible);
  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    let active = true;
    progress.stopAnimation();
    if (visible) setMounted(true);
    const finish = () => {
      progress.stopAnimation();
      progress.setValue(visible ? 1 : 0);
      if (!visible) setMounted(false);
    };
    const subscription = AccessibilityInfo.addEventListener('reduceMotionChanged', reduced => {if (active && reduced) finish();});
    AccessibilityInfo.isReduceMotionEnabled().then(reduced => {
      if (!active) return;
      if (reduced) {finish(); return;}
      Animated.timing(progress, {toValue: visible ? 1 : 0, duration: visible ? 220 : 170, useNativeDriver: true}).start(({finished} = {}) => {
        if (active && finished && !visible) setMounted(false);
      });
    }).catch(() => {if (active) finish();});
    return () => {active = false; subscription.remove(); progress.stopAnimation();};
  }, [visible, progress]);
  return <Modal visible={mounted} transparent animationType="none" onRequestClose={onClose}>
    <SafeAreaProvider><View style={styles.root}>
      <Animated.View style={[StyleSheet.absoluteFillObject, {backgroundColor: 'rgba(20,34,31,.42)', opacity: progress}]}/>
      <Pressable style={StyleSheet.absoluteFillObject} accessibilityRole="button" accessibilityLabel="Cerrar menú" onPress={onClose}/>
      <Animated.View pointerEvents={visible ? 'auto' : 'none'} accessibilityViewIsModal style={[styles.panel, {opacity: progress, transform: [{translateY: progress.interpolate({inputRange: [0, 1], outputRange: [-28, 0]})}]}]}>
        <SafeAreaView style={{flexShrink: 1}} edges={['top', 'left', 'right']}><ScrollView contentContainerStyle={styles.content}>{children}</ScrollView></SafeAreaView>
      </Animated.View>
    </View></SafeAreaProvider>
  </Modal>;
}
const styles = StyleSheet.create({
  root: {flex: 1}, panel: {maxHeight: '90%', backgroundColor: '#fff', borderBottomLeftRadius: 28, borderBottomRightRadius: 28, overflow: 'hidden'},
  content: {paddingHorizontal: 18, paddingTop: 10, paddingBottom: 24, gap: 8},
});
