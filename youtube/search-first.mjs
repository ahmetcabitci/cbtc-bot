import { Innertube } from 'youtubei.js';

const query = process.argv.slice(2).join(' ').trim();
if (!query) {
  console.error('Arama metni bos.');
  process.exit(2);
}

try {
  let results;
  try {
    const fastYoutube = await Innertube.create({
      retrieve_player: false,
      generate_session_locally: true,
    });
    results = await fastYoutube.search(query);
    if (!results.videos?.length) throw new Error('Hızlı arama sonuç vermedi.');
  } catch (fastError) {
    console.error('Hızlı arama kullanılamadı, normal arama deneniyor:', fastError.message);
    const youtube = await Innertube.create();
    results = await youtube.search(query);
  }
  const videos = results.videos.slice(0, 10)
    .map((video) => ({
      id: video.id,
      title: video.title?.toString() || query,
    }))
    .filter((video) => video.id);
  if (!videos.length) throw new Error('Video bulunamadi.');
  const first = videos[0];
  console.log('CBTC_RESULT=' + JSON.stringify({
    id: first.id,
    title: first.title,
    count: videos.length,
    videos,
  }));
} catch (error) {
  console.error('Arama hatasi:', error.message);
  process.exitCode = 1;
}
