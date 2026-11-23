import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generatedImages, imageIdentity, imageLink, uniqueImagePreviews } from '../lib/media.ts';
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
