import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generatedImages, generatedMedia, imageIdentity, imageLink, uniqueImagePreviews } from '../lib/media.ts';
import { parseSessions } from '../lib/history.ts';

const call = {id:'call', type:'tool_call', name:'elevenlabs_creative_generate_image', timestamp:1};
const result = value => ({id:'result', type:'tool_result', name:'elevenlabs_creative_get_flow_run_status', timestamp:2, output:JSON.stringify(value)});
const url = 'https://files.elevenlabsusercontent.com/result?signature=a%2Fb&expires=123';

test('completed images render from tool data without depending on the answer Markdown', () => {
  const thoughts = [call, result({generations:[{status:'completed', content_url:url, content_mime_type:'image/png'}]})];
  assert.deepEqual(generatedImages(thoughts), [{url}]);
  const session = [{id:'thread', messages:[{id:'m', role:'assistant', content:'Here is your image', thoughts}]}];
  assert.deepEqual(generatedImages(parseSessions(JSON.stringify(session))[0].messages[0].thoughts), [{url}]);
});

test('canvas links, failed jobs, prompts, audio and unsafe URLs do not become image previews', () => {
  assert.deepEqual(generatedImages([call, result({
    url:'https://elevenlabs.io/app/flows/123',
    prompt:{image_url:'https://example.com/unrelated.png'},
    generations:[
      {status:'pending',content_url:url}, {status:'failed',content_url:url},
      {content_url:'https://example.com/audio.mp3',content_mime_type:'audio/mpeg'},
      {content_url:'javascript:alert(1)',content_mime_type:'image/png'},
    ],
  })]), []);
  assert.equal(imageLink('javascript:alert(1)'), false);
  assert.equal(imageLink('https://example.com/picture.webp?signature=123'), true);
});

test('MCP text blocks are parsed, files deduplicated, noncreative tools ignored', () => {
  const block = [{type:'text',text:JSON.stringify({generations:[{content_url:url}]})}];
  const thought = result(block);
  assert.deepEqual(generatedImages([call,thought,thought]), [{url}]);
  assert.deepEqual(generatedImages([{...thought,name:'research_search_arxiv'}]), []);
});

test('refreshed signatures and URL aliases produce one preview with the newest file link', () => {
  const refreshed = url.replace('a%2Fb', 'new-signature').replace('123', '456');
  const thoughts = [call,
    result({generations:[{content_url:url, download_url:'https://example.com/download-alias.png'}]}),
    result({generations:[{content_url:refreshed}]}),
  ];
  assert.deepEqual(generatedImages(thoughts), [{url:refreshed}]);
  assert.equal(imageIdentity(url),imageIdentity(refreshed));
  assert.notEqual(imageIdentity(url), imageIdentity(url+'&width=320'));
  assert.notEqual(imageIdentity(url), imageIdentity(url.replace('/result?', '/different?')));
});

test('Markdown images and download links share the tool preview rather than duplicating it', () => {
  const refreshed = url.replace('a%2Fb', 'new-signature');
  const tree = {type:'root',children:[
    {type:'element',tagName:'img',properties:{src:url}},
    {type:'element',tagName:'img',properties:{src:refreshed}},
    {type:'element',tagName:'a',properties:{href:refreshed},children:[{type:'text',value:'Download'}]},
  ]};
  uniqueImagePreviews({sources:[url],imageContext:true})(tree);
  assert.deepEqual(tree.children.map(node=>node.tagName), ['a']);
});

test('without tool results a repeated Markdown image/link still renders once; distinct files remain', () => {
  const other='https://example.com/other.png';
  const tree = {type:'root',children:[
    {type:'element',tagName:'a',properties:{href:url}},
    {type:'element',tagName:'img',properties:{src:url}},
    {type:'element',tagName:'a',properties:{href:url}},
    {type:'element',tagName:'img',properties:{src:other}},
  ]};
  uniqueImagePreviews({sources:[],imageContext:true})(tree);
  assert.deepEqual(tree.children.map(node=>node.tagName), ['img','a','img']);
});

test('one generation with different CDN paths is deduplicated by provider ID', () => {
  const latest = 'https://another.elevenlabsusercontent.com/a-new-path?token=fresh';
  const thoughts = [call, result({generations:[{id:'generation-1',content_url:url}]}), result({generations:[{id:'generation-1',content_url:latest}]})];
  assert.deepEqual(generatedMedia(thoughts), [{url:latest,kind:'image',generationId:'generation-1'}]);
  thoughts.push(result({generations:[{id:'generation-2',content_url:'https://example.com/second.png'}]}));
  assert.equal(generatedMedia(thoughts).length,2);
});

test('tool files are authoritative when the writer repeats the image at a different URL', () => {
  const tree = {type:'root',children:[{type:'element',tagName:'img',properties:{src:'https://other.example/duplicate.png'}}, {type:'element',tagName:'a',properties:{href:'https://other.example/duplicate.png'}}]};
  uniqueImagePreviews({sources:[url],imageContext:true,authoritative:true})(tree);
  assert.deepEqual(tree.children.map(node=>node.tagName),['a']);
});

test('speech and music results become audio files rather than broken image previews', () => {
  const speech = {id:'speech',type:'tool_call',name:'elevenlabs_creative_generate_speech',timestamp:3};
  const sound = 'https://files.elevenlabsusercontent.com/speech?token=audio';
  const thoughts = [speech, result({generations:[{id:'speech-1',status:'completed',content_url:sound,content_mime_type:'audio/mpeg'}]})];
  assert.deepEqual(generatedMedia(thoughts),[{url:sound,kind:'audio',generationId:'speech-1'}]);
  assert.deepEqual(generatedImages(thoughts),[]);
  assert.deepEqual(generatedMedia([result({audio_url:sound})]),[{url:sound,kind:'audio'}]);
  const music=[{...speech,name:'elevenlabs_creative_generate_in_flow'},result({generations:[{id:'music-1',status:'completed',content_url:sound,content_mime_type:'audio/wav'}]})];
  assert.equal(generatedMedia(music)[0].kind,'audio');
  assert.deepEqual(generatedMedia([speech,result({generations:[{status:'failed',content_url:sound,content_mime_type:'audio/mpeg'}]})]),[]);
});

test('actual provider generation and media records share one master file', () => {
  for (const kind of ['audio','image']) {
    const master = `https://elevenlabsusercontent.com/generation/master.${kind==='audio'?'mp3':'png'}?Expires=123&KeyName=cdn-key&Signature=signed`;
    const thought = result({
      generations:[{id:'same-id',status:'completed',modality:kind,content_url:`https://cdn.example/preview.${kind==='audio'?'mp3':'png'}`}],
      media:[{generation_id:'same-id',kind,master_url:master}],
    });
    assert.deepEqual(generatedMedia([thought]),[{url:master,kind,generationId:'same-id'}]);
    assert.deepEqual(generatedMedia([result({media:[{generation_id:'same-id',kind,master_url:master}]})]),[{url:master,kind,generationId:'same-id'}]);
  }
});
