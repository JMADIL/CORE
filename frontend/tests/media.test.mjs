import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generatedImages, imageLink } from '../lib/media.ts';
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
