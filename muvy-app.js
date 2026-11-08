(() => {
  const isHomePage=document.body.classList.contains('home-body')&&!document.body.classList.contains('explore-body');
  const bindBackControl=control=>{
    if(control.dataset.appBackBound)return;
    control.dataset.appBackBound='true';
    control.addEventListener('click',event=>{
      if(window.history.length>1){
        event.preventDefault();
        window.history.back();
      }
    });
  };
  document.querySelectorAll('[data-app-back]').forEach(bindBackControl);
  const header=document.querySelector('.muvy-header');
  const brandSide=header?.querySelector('.brand-side');
  if(brandSide&&!isHomePage&&!document.querySelector('[data-app-back]')){
    const backLink=document.createElement('a');
    backLink.className='muvy-history-back';
    backLink.href='home.html';
    backLink.dataset.appBack='';
    backLink.setAttribute('aria-label','Go back to previous page');
    backLink.title='Go back';
    backLink.innerHTML='<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m15 18-6-6 6-6M9 12h11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    brandSide.prepend(backLink);
    bindBackControl(backLink);
  }
  const menuButton=isHomePage?document.querySelector('#app-menu-button'):null;
  const menuPanel=isHomePage?document.querySelector('#app-menu-panel'):null;
  let menuBackdrop;
  let menuCloseTimer;
  const menuMarkup = `
    <div class="menu-brand-row"><a class="menu-wordmark" href="home.html" aria-label="MUVY home">MU<span>V</span>Y</a><button class="menu-close" type="button" aria-label="Close menu">×</button></div>
    <a class="menu-account" href="profile.html"><span class="menu-avatar" data-menu-avatar aria-hidden="true">M</span><span class="menu-account-copy"><strong data-menu-name>My Profile</strong><small data-menu-account-detail></small></span><span class="menu-account-arrow" aria-hidden="true">›</span></a>
    <div class="menu-divider" aria-hidden="true"></div>
    <a class="menu-option" href="settings.html#premium"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2.5 2.8 5.8 6.4.9-4.6 4.5 1.1 6.4-5.7-3-5.7 3 1.1-6.4-4.6-4.5 6.4-.9z" fill="currentColor"/></svg><span>Upgrade Plan</span></a>
    <a class="menu-option" href="watchlist.html"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.75A1.75 1.75 0 0 1 7.75 2h8.5A1.75 1.75 0 0 1 18 3.75V22l-6-3.8L6 22z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg><span>Bookmarks</span></a>
    <a class="menu-option" href="app-info.html#rate"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg><span>Rate Our App</span></a>
    <button class="menu-option" type="button" data-menu-share><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="6" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="18" cy="19" r="3" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="m8.7 10.6 6.6-4.2m-6.6 7 6.6 4.2" fill="none" stroke="currentColor" stroke-width="1.7"/></svg><span>Share with Friends</span></button>
    <a class="menu-option" href="app-info.html#contact"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v12H9l-5 4z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8 9h8m-8 4h5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg><span>Contact Us</span></a>
    <a class="menu-option" href="app-info.html#privacy"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 20 6v5c0 5-3.4 8.2-8 10-4.6-1.8-8-5-8-10V6z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="m9 12 2 2 4-4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Privacy Policy</span></a>
    <a class="menu-option" href="app-info.html#terms"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l4 4v14H6z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M14 3v5h5m-9 4h5m-5 4h5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Terms and Conditions</span></a>
    <a class="menu-option" href="settings.html"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="m19.4 15 .1.1a1.7 1.7 0 0 1-2.4 2.4l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.2a1.7 1.7 0 0 1-3.4 0v-.2a1.7 1.7 0 0 0-2.9-1.2l-.1.1a1.7 1.7 0 0 1-2.4-2.4l.1-.1a1.7 1.7 0 0 0-1.2-2.9H4a1.7 1.7 0 0 1 0-3.4h.2a1.7 1.7 0 0 0 1.2-2.9l-.1-.1a1.7 1.7 0 0 1 2.4-2.4l.1.1a1.7 1.7 0 0 0 2.9-1.2V2a1.7 1.7 0 0 1 3.4 0v.2a1.7 1.7 0 0 0 2.9 1.2l.1-.1a1.7 1.7 0 0 1 2.4 2.4l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.2a1.7 1.7 0 0 1 0 3.4h-.2a1.7 1.7 0 0 0-1.2 2.9z" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Settings</span></a>
    <label class="menu-theme-row"><span>Light/Dark Mode</span><input type="checkbox" role="switch" data-theme-toggle aria-label="Light/Dark Mode"><i aria-hidden="true"></i></label>`;
  if(menuButton&&menuPanel){
    menuPanel.className='muvy-menu';
    menuPanel.innerHTML=menuMarkup;
    const account=window.MUVYAuth?.getSession();
    const accountName=account?.name?.trim()||account?.email?.split('@')[0]?.replace(/[._-]+/g,' ').trim();
    const menuName=menuPanel.querySelector('[data-menu-name]');
    const menuDetail=menuPanel.querySelector('[data-menu-account-detail]');
    const menuAvatar=menuPanel.querySelector('[data-menu-avatar]');
    if(accountName)menuName.textContent=accountName;
    if(account?.email)menuDetail.textContent=account.email;
    if(accountName)menuAvatar.textContent=accountName.slice(0,1).toUpperCase();
    menuPanel.hidden=true;
    menuPanel.inert=true;
    menuPanel.setAttribute('aria-hidden','true');
    menuButton.setAttribute('aria-expanded','false');
    menuBackdrop=document.createElement('button');
    menuBackdrop.className='muvy-menu-backdrop';
    menuBackdrop.type='button';
    menuBackdrop.setAttribute('aria-label','Close menu');
    menuBackdrop.hidden=true;
    document.body.append(menuBackdrop);
    const closeMenu=()=>{
      if(menuPanel.hidden&&menuPanel.inert)return;
      window.clearTimeout(menuCloseTimer);
      menuButton.setAttribute('aria-expanded','false');
      menuPanel.setAttribute('aria-hidden','true');
      menuPanel.inert=true;
      menuPanel.classList.remove('is-open');
      menuBackdrop.classList.remove('is-open');
      document.body.classList.remove('muvy-menu-open');
      menuCloseTimer=window.setTimeout(()=>{menuPanel.hidden=true;menuBackdrop.hidden=true},220);
    };
    const openMenu=()=>{
      window.clearTimeout(menuCloseTimer);
      menuPanel.hidden=false;
      menuBackdrop.hidden=false;
      menuPanel.inert=false;
      menuPanel.setAttribute('aria-hidden','false');
      menuButton.setAttribute('aria-expanded','true');
      document.body.classList.add('muvy-menu-open');
      window.requestAnimationFrame(()=>{menuPanel.classList.add('is-open');menuBackdrop.classList.add('is-open')});
    };
    menuButton.setAttribute('aria-controls',menuPanel.id);
    menuButton.addEventListener('click',()=>menuPanel.hidden?openMenu():closeMenu());
    menuPanel.querySelector('.menu-close').addEventListener('click',closeMenu);
    menuBackdrop.addEventListener('click',closeMenu);
    menuPanel.querySelectorAll('a').forEach(link=>link.addEventListener('click',closeMenu));
    menuPanel.querySelector('[data-menu-share]').addEventListener('click',async()=>{
      closeMenu();
      const shareData={title:'MUVY',text:'Discover any movie. Find your next favourite.',url:new URL('home.html',document.baseURI).href};
      try{
        if(navigator.share)await navigator.share(shareData);
        else if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(shareData.url);showToast('MUVY link copied.')}
        else throw new Error('Sharing is not supported in this browser.');
      }catch(error){
        if(error.name!=='AbortError'){console.error('MUVY sharing failed:',error);showToast('Unable to share MUVY from this browser.')}
      }
    });
    const resetMenu=()=>{
      window.clearTimeout(menuCloseTimer);
      menuPanel.classList.remove('is-open');
      menuBackdrop.classList.remove('is-open');
      menuPanel.hidden=true;
      menuBackdrop.hidden=true;
      document.body.classList.remove('muvy-menu-open');
      menuPanel.inert=true;
      menuPanel.setAttribute('aria-hidden','true');
      menuButton.setAttribute('aria-expanded','false');
    };
    window.addEventListener('pageshow',resetMenu);
    window.addEventListener('pagehide',resetMenu);
    document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu()});
  }
  const storageKey='muvy.savedMovies';
  const getSaved=()=>{try{return JSON.parse(localStorage.getItem(storageKey)||'[]')}catch{return[]}};
  const setSaved=items=>localStorage.setItem(storageKey,JSON.stringify(items));
  document.querySelectorAll('[data-bookmark]').forEach(button=>{
    const title=button.dataset.bookmark;
    const card=button.closest('.cover-card,.trend-card');
    const link=card?.querySelector('.movie-card');
    const image=card?.querySelector('img')?.getAttribute('src')||'';
    const saved=getSaved().some(item=>item.title===title);
    button.classList.toggle('is-saved',saved);button.setAttribute('aria-pressed',String(saved));
    button.textContent='';
    button.addEventListener('click',event=>{
      event.preventDefault();event.stopPropagation();
      const list=getSaved();const index=list.findIndex(item=>item.title===title);
      if(index>=0){list.splice(index,1);button.classList.remove('is-saved');button.setAttribute('aria-pressed','false');button.textContent='';showToast(`${title} removed from Bookmarks`)}
      else{list.push({title,image,year:link?.dataset.year||'',genres:link?.dataset.genres||''});button.classList.add('is-saved');button.setAttribute('aria-pressed','true');button.textContent='';showToast(`${title} added to Bookmarks`)}
      setSaved(list);
    });
  });
  function showToast(message){const toast=document.querySelector('#toast,#explore-toast');if(!toast)return;toast.textContent=message;toast.classList.add('is-visible');clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>toast.classList.remove('is-visible'),2400)}
  const greetingTitle=document.getElementById('greeting-title');
  if(greetingTitle){
    let greetingTimer;
    const updateGreeting=()=>{
      const currentAccount=window.MUVYAuth?.getSession();
      const emailName=currentAccount?.email?.split('@')[0].replace(/[._-]+/g,' ').trim();
      const displayName=currentAccount?.name?.trim()||emailName;
      const firstName=displayName?.split(/\s+/)[0]||'Mudy';
      const now=new Date();
      const timeGreeting=now.getHours()<12?'Good morning':now.getHours()<17?'Good afternoon':'Good evening';
      greetingTitle.textContent=`${window.MUVYLocale?.t(timeGreeting)??timeGreeting}, ${firstName}!`;
      const millisecondsUntilNextHour=(60-now.getMinutes())*60000-now.getSeconds()*1000-now.getMilliseconds();
      window.clearTimeout(greetingTimer);
      greetingTimer=window.setTimeout(updateGreeting,millisecondsUntilNextHour+50);
    };
    updateGreeting();
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)updateGreeting()});
  }
  const heroCarousel=document.querySelector('[data-hero-carousel]');
  if(heroCarousel){
    const slides=[...heroCarousel.querySelectorAll('[data-hero-slide]')];
    const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
    let activeSlide=0;
    let timer;
    let interacting=false;
    const setSlide=(nextIndex)=>{
      activeSlide=(nextIndex+slides.length)%slides.length;
      heroCarousel.dataset.activeSlide=String(activeSlide);
      slides.forEach((slide,index)=>{
        const active=index===activeSlide;
        slide.classList.toggle('is-active',active);
        slide.setAttribute('aria-hidden',String(!active));
      });
    };
    const clearTimer=()=>window.clearInterval(timer);
    const startTimer=()=>{
      clearTimer();
      if(!interacting&&!reducedMotion.matches&&!document.hidden){
        timer=window.setInterval(()=>setSlide(activeSlide+1),6500);
      }
    };
    heroCarousel.addEventListener('pointerenter',()=>{interacting=true;clearTimer()});
    heroCarousel.addEventListener('pointerleave',()=>{interacting=false;startTimer()});
    heroCarousel.addEventListener('focusin',()=>{interacting=true;clearTimer()});
    heroCarousel.addEventListener('focusout',event=>{
      if(!heroCarousel.contains(event.relatedTarget)){interacting=false;startTimer()}
    });
    document.addEventListener('visibilitychange',startTimer);
    reducedMotion.addEventListener?.('change',startTimer);
    setSlide(activeSlide);
    startTimer();
  }
  const coverflow=document.querySelector('[data-coverflow]');
  if(coverflow){
    const cards=[...coverflow.querySelectorAll('.cover-card')];
    let index=Math.max(0,cards.findIndex(card=>card.classList.contains('cover-focus')));
    let pointerId=null;
    let pointerStartX=0;
    let pointerStartY=0;
    let pointerDeltaX=0;
    let dragging=false;
    let suppressClick=false;
    let wheelDelta=0;
    let wheelLocked=false;
    let wheelResetTimer;
    const render=()=>{
      const step=Math.min(coverflow.clientWidth*.37,(cards[0]?.getBoundingClientRect().width||0)*.92);
      cards.forEach((card,cardIndex)=>{
        let distance=(cardIndex-index+cards.length)%cards.length;
        if(distance>cards.length/2)distance-=cards.length;
        if(cards.length%2===0&&Math.abs(distance)===cards.length/2)distance=-Math.sign(lastDirection||1)*Math.abs(distance);
        const depth=Math.abs(distance);
        const visible=depth<=2;
        const scale=depth===0?1:depth===1?.84:.68;
        card.classList.toggle('cover-focus',depth===0);
        card.classList.toggle('cover-left',distance<0&&visible);
        card.classList.toggle('cover-right',distance>0&&visible);
        card.style.setProperty('--cover-x',`${distance*step}px`);
        card.style.setProperty('--cover-z',`${depth===0?0:depth===1?-82:-180}px`);
        card.style.setProperty('--cover-scale',String(scale));
        card.style.setProperty('--cover-rotation',`${distance===0?0:distance<0?17:-17}deg`);
        card.style.zIndex=String(20-depth);
        card.style.opacity=visible?String(depth===0?1:depth===1?.78:.38):'0';
        card.style.filter=depth===0?'none':`saturate(${depth===1?.78:.5}) blur(${depth===1?0:1}px)`;
        card.style.pointerEvents=visible?'':'none';
        card.setAttribute('aria-hidden',String(!visible));
      });
    };
    let lastDirection=1;
    const shift=direction=>{
      if(cards.length<2)return;
      lastDirection=direction;
      index=(index+direction+cards.length)%cards.length;
      render();
    };
    const clearDrag=()=>{
      coverflow.classList.remove('is-dragging');
      coverflow.style.removeProperty('--coverflow-drag');
      coverflow.style.removeProperty('--coverflow-drag-progress');
      pointerId=null;
      pointerDeltaX=0;
      dragging=false;
    };
    cards.forEach(card=>card.querySelectorAll('a,img').forEach(element=>{element.draggable=false}));
    coverflow.setAttribute('role','region');
    coverflow.setAttribute('aria-roledescription','carousel');
    coverflow.tabIndex=0;
    const resizeObserver=new ResizeObserver(render);
    resizeObserver.observe(coverflow);
    coverflow.addEventListener('keydown',event=>{
      if(event.key==='ArrowRight'){event.preventDefault();shift(1)}
      if(event.key==='ArrowLeft'){event.preventDefault();shift(-1)}
    });
    coverflow.addEventListener('pointerdown',event=>{
      if(event.button!==0||event.target.closest('.bookmark-toggle')||pointerId!==null)return;
      pointerId=event.pointerId;
      pointerStartX=event.clientX;
      pointerStartY=event.clientY;
      pointerDeltaX=0;
      dragging=false;
    });
    coverflow.addEventListener('pointermove',event=>{
      if(event.pointerId!==pointerId)return;
      pointerDeltaX=event.clientX-pointerStartX;
      const deltaY=event.clientY-pointerStartY;
      if(!dragging&&Math.abs(pointerDeltaX)>8&&Math.abs(pointerDeltaX)>Math.abs(deltaY)){
        dragging=true;
        coverflow.classList.add('is-dragging');
        coverflow.setPointerCapture(pointerId);
      }
      if(dragging){
        const maxDrag=coverflow.clientWidth*.42;
        const boundedDrag=Math.max(-maxDrag,Math.min(maxDrag,pointerDeltaX));
        coverflow.style.setProperty('--coverflow-drag',`${boundedDrag}px`);
        coverflow.style.setProperty('--coverflow-drag-progress',String(boundedDrag/Math.max(1,maxDrag)));
        event.preventDefault();
      }
    });
    const finishDrag=event=>{
      if(event.pointerId!==pointerId)return;
      if(dragging){
        const threshold=Math.max(38,coverflow.clientWidth*.12);
        if(Math.abs(pointerDeltaX)>=threshold)shift(pointerDeltaX<0?1:-1);
        suppressClick=true;
        window.setTimeout(()=>{suppressClick=false},0);
      }
      clearDrag();
    };
    coverflow.addEventListener('pointerup',finishDrag);
    coverflow.addEventListener('pointercancel',event=>{if(event.pointerId===pointerId)clearDrag()});
    coverflow.addEventListener('lostpointercapture',event=>{if(event.target===coverflow)clearDrag()});
    coverflow.addEventListener('click',event=>{
      if(!suppressClick)return;
      event.preventDefault();
      event.stopPropagation();
      suppressClick=false;
    },true);
    coverflow.addEventListener('wheel',event=>{
      if(Math.abs(event.deltaX)<4||Math.abs(event.deltaX)<=Math.abs(event.deltaY)*1.25)return;
      event.preventDefault();
      window.clearTimeout(wheelResetTimer);
      wheelDelta+=event.deltaX;
      if(!wheelLocked&&Math.abs(wheelDelta)>=48){
        shift(wheelDelta<0?1:-1);
        wheelLocked=true;
      }
      wheelResetTimer=window.setTimeout(()=>{wheelDelta=0;wheelLocked=false},180);
    },{passive:false});
    render();
  }
  document.querySelectorAll('[data-chat-prompt]').forEach(button=>button.addEventListener('click',()=>{const input=document.getElementById('ai-input');if(input){input.value=button.dataset.chatPrompt;input.focus()}}));
  const chatForm=document.getElementById('ai-chat-form');
  chatForm?.addEventListener('submit',e=>{e.preventDefault();const input=document.getElementById('ai-input');const text=input?.value.trim();if(!text)return;const log=document.getElementById('ai-chat-log');const user=document.createElement('div');user.className='chat-bubble user-bubble';user.textContent=text;log.append(user);const reply=document.createElement('div');reply.className='chat-bubble assistant-bubble';reply.textContent='MUVY AI discovery is being connected. Your prompt is ready for the discovery engine in a later integration step.';log.append(reply);input.value='';log.scrollTop=log.scrollHeight;});
  const savedGrid=document.getElementById('saved-movies-grid');
  if(savedGrid){const list=getSaved();if(!list.length){savedGrid.innerHTML='<div class="saved-empty"><span>▣</span><h2>Your collection starts here</h2><p>Bookmark movies anywhere in MUVY and they will appear here.</p><a href="home.html">Browse movies</a></div>'}else{savedGrid.innerHTML=list.map(item=>`<article class="saved-card"><img src="${escapeHtml(item.image)}" alt=""><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.genres||'Bookmarked movie')}</small><button type="button" data-remove-saved="${escapeHtml(item.title)}">Remove</button></div></article>`).join('');savedGrid.querySelectorAll('[data-remove-saved]').forEach(button=>button.addEventListener('click',()=>{setSaved(getSaved().filter(item=>item.title!==button.dataset.removeSaved));location.reload()}));}}
  function escapeHtml(value){return String(value||'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))}
})();
