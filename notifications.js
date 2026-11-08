(() => {
  const emptyState=document.getElementById('notification-empty');
  const listSection=document.getElementById('notification-list');
  const list=document.getElementById('notification-list-items');
  if(!emptyState||!listSection||!list)return;

  const render=notifications=>{
    list.replaceChildren();
    if(!Array.isArray(notifications)||notifications.length===0){
      emptyState.hidden=false;
      listSection.hidden=true;
      return;
    }

    notifications.forEach(notification=>{
      if(!notification||typeof notification.title!=='string'||typeof notification.message!=='string')return;
      const item=notification.href?document.createElement('a'):document.createElement('article');
      item.className=`notification-item${notification.read===false?' is-unread':''}`;
      if(notification.href)item.href=notification.href;
      const icon=document.createElement('span');
      icon.className='notification-item-icon';
      icon.setAttribute('aria-hidden','true');
      icon.textContent='✦';
      const copy=document.createElement('div');
      copy.className='notification-item-copy';
      const title=document.createElement('strong');
      title.textContent=notification.title;
      const message=document.createElement('p');
      message.textContent=notification.message;
      copy.append(title,message);
      if(typeof notification.createdAt==='string'){
        const time=document.createElement('time');
        const date=new Date(notification.createdAt);
        if(!Number.isNaN(date.getTime())){
          time.dateTime=date.toISOString();
          time.textContent=new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(date);
          copy.append(time);
        }
      }
      item.append(icon,copy);
      if(notification.read===false){
        const unread=document.createElement('span');
        unread.className='notification-unread-dot';
        unread.setAttribute('aria-label','Unread');
        item.append(unread);
      }
      list.append(item);
    });

    emptyState.hidden=list.childElementCount>0;
    listSection.hidden=list.childElementCount===0;
  };

  window.MUVYNotificationCenter={render};
  render(window.MUVYNotifications);
})();
