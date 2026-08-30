import { StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
export default function HomeScreen() {
  return <View style={styles.container}><Text accessibilityRole="header" style={styles.title}>PES Mobile</Text><Text style={styles.body}>The mobile application surface is ready. Product features must be delivered through approved vertical slices.</Text><StatusBar style="auto" /></View>;
}
const styles = StyleSheet.create({ container:{flex:1,justifyContent:'center',padding:24,gap:12}, title:{fontSize:28,fontWeight:'700'}, body:{fontSize:17,lineHeight:25} });
