const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const Module = require('node:module');
const root = path.resolve(__dirname, '..');
const mobile = Module.createRequire(path.join(root, 'mobile/package.json'));
const review = Module.createRequire(path.join(root, 'tmp/mobile-review/package.json'));
const React = review('react');
const {create, act} = review('react-test-renderer');
global.IS_REACT_ACT_ENVIRONMENT = true;
test('discovery requests location only explicitly, keeps filters in pagination and resets', async () => {
  let permissions = 0;
  const filename = path.join(root, 'mobile/AdoptionBrowser.js');
  const compiled = new Module(filename, module);
  compiled.require = name => ({react: React, 'react-native': {
    View:'View', Text:'Text', TextInput:'TextInput', Pressable:'Pressable', ScrollView:'ScrollView', ActivityIndicator:'ActivityIndicator', StyleSheet:{create:x=>x},
  }, 'expo-location': {Accuracy:{Balanced:3}, requestForegroundPermissionsAsync:async()=>{permissions++; return {status:'granted'};}, getCurrentPositionAsync:async()=>({coords:{latitude:-34.61234, longitude:-58.43234}})}}[name] || mobile(name));
  compiled._compile(mobile('@babel/core').transformSync(fs.readFileSync(filename,'utf8'), {
    filename,babelrc:false,configFile:false,presets:[mobile.resolve('@babel/preset-react')],plugins:[mobile.resolve('@babel/plugin-transform-modules-commonjs')],
  }).code,filename);
  const urls = [];
  let renderer;
  await act(async()=> {renderer=create(React.createElement(compiled.exports.default, {
    api:'https://example.test',token:'test',renderItem:()=>null,
    request:async url=>{urls.push(new URL(url)); return {ok:true,json:async()=>({adoptions:[],total:61,page:Number(new URL(url).searchParams.get('page')),has_next:true,shelters:[]})};},
  }));});
  const press = async label => act(async()=>renderer.root.findAllByType('Pressable').find(x=>x.findByType('Text').props.children===label).props.onPress());
  assert.equal(permissions,0);
  await act(async()=>renderer.root.findByProps({accessibilityLabel:'Localidad del animal'}).props.onChangeText('La Plata'));
  await press('Mi ubicación');
  await press('25 km');
  await press('Aplicar filtros');
  assert.equal(permissions,1);
  assert.equal(urls.at(-1).searchParams.get('lat'),'-34.61');
  assert.equal(urls.at(-1).searchParams.get('radius'),'25');
  await press('Siguiente');
  assert.equal(urls.at(-1).searchParams.get('page'),'2');
  assert.equal(urls.at(-1).searchParams.get('locality'),'La Plata');
  await press('Limpiar');
  assert.equal(urls.at(-1).searchParams.has('lat'),false);
  assert.equal(urls.at(-1).searchParams.has('radius'),false);
  await act(async()=>renderer.unmount());
});
